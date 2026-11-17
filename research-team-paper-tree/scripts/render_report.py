"""Render the two views of a researched paper tree from one JSON record."""

import argparse
from collections import Counter, defaultdict
from datetime import date
from html import escape
import json
from pathlib import Path
import re
from string import Template
from urllib.parse import quote, urlsplit


LABELS = {
    "seed": ("原论文", "Seed paper"),
    "reading": ("第一次读，从这里开始", "Where to start"),
    "clues": ("从原论文找到的线索", "Clues from the seed paper"),
    "tree": ("研究分支与论文关系", "Research branches and paper relationships"),
    "profile": ("团队简介", "Group profile"),
    "external": ("外组论文", "External paper"),
    "coverage": ("检索范围与待核实项", "Search coverage and open questions"),
    "found_by": ("怎么找到的", "How it was found"),
    "reason": ("为什么收录", "Why it belongs here"),
    "note": ("版本与待核实信息", "Versions and open questions"),
    "affiliation": ("团队或机构", "Group or institution"),
    "unknown": ("日期待核实", "Date unverified"),
    "empty": ("暂无已核实的相关成果。", "No related work has been verified."),
    "markdown": ("打开 Markdown 完整报告", "Open the full Markdown report"),
    "html": ("打开交互论文树", "Open the interactive paper tree"),
}
PAPER_FIELDS = ("affiliation", "found_by", "reason", "note")
ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}")


def validate_date(value):
    if not value:
        return
    if not re.fullmatch(r"\d{4}(?:-\d{2}(?:-\d{2})?)?", value):
        raise ValueError(f"Invalid publication date: {value}")
    date.fromisoformat((value + "-01-01")[:10])


def source_url(value):
    parsed = urlsplit(value)
    if parsed.scheme not in {"https", "http"} or not parsed.hostname or any(c.isspace() for c in value):
        raise ValueError(f"Invalid source URL: {value}")
    return value


def validate(data):
    papers = {}
    for paper in data["papers"]:
        paper_id = paper["id"]
        if not ID.fullmatch(paper_id) or paper_id in papers:
            raise ValueError(f"Invalid or duplicate paper ID: {paper_id}")
        validate_date(paper["date"])
        if not paper["sources"]:
            raise ValueError(f"Paper requires a source: {paper_id}")
        papers[paper_id] = paper

    included = {data["seed"]}
    for group in data["groups"]:
        ids = [paper_id for branch in group["branches"] for paper_id in branch["papers"]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"A paper is listed twice in group: {group['name']}")
        included.update(ids)

    external = set()
    for relation in data["relations"]:
        if relation["anchor"] not in included or relation["paper"] in included:
            raise ValueError(f"An external relation must join a group paper or seed to an external paper: {relation}")
        if not relation["type"].strip() or not relation["evidence"].strip() or not relation["sources"]:
            raise ValueError("An external relation needs a type and sourced evidence")
        external.add(relation["paper"])

    used = included | external
    if set(papers) != used:
        raise ValueError(f"Paper records and referenced IDs differ: {sorted(set(papers) ^ used)}")
    for paper_id in [data["seed"], *(item["paper"] for item in data["reading"])]:
        paper = papers[paper_id]
        if not paper.get("found_by") or not paper.get("reason"):
            raise ValueError(f"Seed and reading-route papers need discovery and inclusion reasons: {paper_id}")
    return papers


def md_text(value):
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", escape(value, quote=False))


def md_block(value):
    # Keep paragraphs while preventing supplied text from introducing block syntax.
    parts = []
    for paragraph in re.split(r"\n\s*\n", value):
        parts.append(md_text(" ".join(paragraph.split())))
    return "\n\n".join(parts)


def html_text(value):
    return "".join(f"<p>{escape(' '.join(p.split()))}</p>" for p in re.split(r"\n\s*\n", value) if p.strip())


class Report:
    def __init__(self, data, filename):
        self.data = data
        self.papers = validate(data)
        self.filename = filename
        self.chinese = data["lang"].lower().startswith("zh")
        self.relations = defaultdict(list)
        for relation in data["relations"]:
            self.relations[relation["anchor"]].append(relation)
        self.occurrences = Counter()

    def label(self, key):
        return LABELS[key][0 if self.chinese else 1]

    def date(self, paper):
        return paper["date"] or self.label("unknown")

    def branch_papers(self, branch):
        return sorted(
            (self.papers[key] for key in branch["papers"]),
            key=lambda paper: (not paper["date"], paper["date"], paper["title"].casefold()),
        )

    def fields(self, paper):
        yield from ((self.label(key), paper[key]) for key in PAPER_FIELDS if paper.get(key))

    def next_anchor(self, paper_id):
        self.occurrences[paper_id] += 1
        count = self.occurrences[paper_id]
        return f"paper-{paper_id}" if count == 1 else f"paper-{paper_id}:{count}"

    @staticmethod
    def links(sources, html=False):
        links = []
        for item in sources:
            url = source_url(item["url"])
            if html:
                links.append(f'<a href="{escape(url)}" target="_blank" rel="noopener noreferrer">{escape(item["label"])}</a>')
            else:
                links.append(f'[{md_text(item["label"])}](<{url}>)')
        return (' <span aria-hidden="true">·</span> ' if html else " · ").join(links)

    def md_notes(self, notes):
        return "\n\n".join(
            f'**{md_text(note["title"])}**\n\n{md_block(note["text"])}'
            + (f'\n\n{self.links(note["sources"])}' if note.get("sources") else "")
            for note in notes
        )

    def html_notes(self, notes):
        return "".join(
            f'<section class="note"><h3>{escape(note["title"])}</h3>{html_text(note["text"])}'
            f'<div class="links">{self.links(note.get("sources", []), html=True)}</div></section>'
            for note in notes
        )

    def md_paper(self, paper, level=4):
        tag = f' · {self.label("seed")}' if paper["id"] == self.data["seed"] else ""
        title = paper.get("label") or paper["title"]
        heading = f'{"#" * level} {md_text(paper["id"])} · {self.date(paper)}{tag} · {md_text(title)}'
        original = f'*{md_text(paper["title"])}*' if title != paper["title"] else ""
        meta = " · ".join(md_text(paper[key]) for key in ("authors", "venue") if paper.get(key))
        details = [heading, original, meta, md_block(paper["summary"])]
        details.extend(f"**{label}**　{md_block(value)}" for label, value in self.fields(paper))
        details.append(self.links(paper["sources"]))
        return "\n\n".join(part for part in details if part)

    def md_relations(self, paper_id):
        items = []
        for edge in self.relations[paper_id]:
            paper = self.papers[edge["paper"]]
            items.append(
                f'**{self.label("external")} · {md_text(edge["type"])}**\n\n'
                f'{md_block(edge["evidence"])}\n\n{self.links(edge["sources"])}\n\n{self.md_paper(paper, level=5)}'
            )
        return "\n\n".join(items)

    def markdown(self):
        data = self.data
        seed = self.papers[data["seed"]]
        filename = quote(self.filename, safe="")
        parts = [
            f'# {md_text(data["title"])}', md_block(data["overview"]),
            f'[{self.label("html")}]({filename}.html)',
        ]
        reading = [
            f'{i}. **{md_text(item["paper"])} · {md_text(self.papers[item["paper"]].get("label") or self.papers[item["paper"]]["title"])}**　{md_text(" ".join(item["reason"].split()))}'
            for i, item in enumerate(data["reading"], 1)
        ]
        if reading:
            parts.extend([f'## {self.label("reading")}', "\n".join(reading)])
        if data["clues"]:
            parts.extend([f'## {self.label("clues")}', self.md_notes(data["clues"])])
        listed = any(data["seed"] in branch["papers"] for group in data["groups"] for branch in group["branches"])
        if not listed:
            parts.extend([f'## {self.label("seed")}', self.md_paper(seed, level=3), self.md_relations(seed["id"])])
        for group in data["groups"]:
            parts.append(f'## {md_text(group["name"])}')
            if not group["branches"]:
                parts.append(self.label("empty"))
            for branch in group["branches"]:
                parts.extend([f'### {md_text(branch["kind"])} · {md_text(branch["title"])}', md_block(branch["story"])])
                for paper in self.branch_papers(branch):
                    parts.extend([self.md_paper(paper), self.md_relations(paper["id"])])
            if group["profile"]:
                parts.extend([f'### {self.label("profile")}', self.md_notes(group["profile"])])
        parts.extend([f'## {self.label("coverage")}', self.md_notes(data["coverage"])])
        return "\n\n".join(part for part in parts if part) + "\n"

    def html_paper(self, paper, external=False):
        paper_id = paper["id"]
        anchor = self.next_anchor(paper_id)
        title = paper.get("label") or paper["title"]
        full_title = f'<p class="original">{escape(paper["title"])}</p>' if title != paper["title"] else ""
        metadata = " · ".join(escape(paper[key]) for key in ("authors", "venue") if paper.get(key))
        tag = f'<span class="badge">{self.label("seed")}</span>' if paper_id == self.data["seed"] else ""
        fields = "".join(f"<dt>{escape(label)}</dt><dd>{html_text(value)}</dd>" for label, value in self.fields(paper))
        edges = "" if external else self.html_relations(paper_id)
        return (
            f'<article class="paper" id="{anchor}" tabindex="-1"><details class="paper-detail">'
            f'<summary><span class="date">{escape(paper_id)} · {escape(self.date(paper))}</span> {tag}'
            f'<span class="paper-title">{escape(title)}</span></summary>'
            f'<div class="paper-body">{full_title}<p class="metadata">{metadata}</p>{html_text(paper["summary"])}'
            f'<dl>{fields}</dl><div class="links">{self.links(paper["sources"], html=True)}</div></div>'
            f'</details>{edges}</article>'
        )

    def html_relations(self, paper_id):
        return "".join(
            f'<div class="relationship"><details><summary><span class="badge external">{self.label("external")}</span>'
            f'<span>{escape(edge["type"])} · {escape(self.papers[edge["paper"]].get("label") or self.papers[edge["paper"]]["title"])}</span>'
            f'</summary><div class="edge-body">{html_text(edge["evidence"])}'
            f'<div class="links">{self.links(edge["sources"], html=True)}</div>'
            f'{self.html_paper(self.papers[edge["paper"]], external=True)}</div></details></div>'
            for edge in self.relations[paper_id]
        )

    def html_reading(self):
        items = "".join(
            f'<li><a href="#paper-{item["paper"]}">{escape(self.papers[item["paper"]].get("label") or self.papers[item["paper"]]["title"])}</a>'
            f'{html_text(item["reason"])}</li>'
            for item in self.data["reading"]
        )
        return f'<section><h2>{self.label("reading")}</h2><ol class="reading">{items}</ol></section>' if items else ""

    def html_group(self, group, index):
        overview, branches = [], []
        for branch_index, branch in enumerate(group["branches"], 1):
            key = f"branch-{index}-{branch_index}"
            name, kind = escape(branch["title"]), escape(branch["kind"])
            overview.append(f'<li><a href="#{key}"><span class="branch-kind">{kind}</span>{name}</a></li>')
            papers = "".join(self.html_paper(paper) for paper in self.branch_papers(branch))
            branches.append(
                f'<details class="branch" id="{key}"><summary><span class="branch-kind">{kind}</span>{name}</summary>'
                f'<div class="branch-body">{html_text(branch["story"])}<div class="timeline">{papers}</div></div></details>'
            )
        group_name = escape(group["name"])
        navigation = f'<ul class="branch-map">{"".join(overview)}</ul>' if overview else f'<p>{self.label("empty")}</p>'
        profile = self.html_notes(group["profile"])
        return (
            f'<section class="group" id="group-{index}" tabindex="-1"><h3>{group_name}</h3>{navigation}{"".join(branches)}'
            + (f'<details class="section-detail"><summary>{self.label("profile")}</summary>{profile}</details>' if profile else "")
            + '</section>'
        )

    def html(self):
        self.occurrences.clear()
        data = self.data
        seed = self.papers[data["seed"]]
        listed = any(data["seed"] in branch["papers"] for group in data["groups"] for branch in group["branches"])
        seed_paper = "" if listed else self.html_paper(seed)
        groups = "".join(self.html_group(group, i) for i, group in enumerate(data["groups"], 1))
        group_map = ""
        if len(data["groups"]) > 1:
            links = "".join(
                f'<li><a href="#group-{i}">{escape(group["name"])}</a></li>'
                for i, group in enumerate(data["groups"], 1)
            )
            group_map = f'<ul class="branch-map group-map">{links}</ul>'
        template = Path(__file__).resolve().parents[1] / "assets" / "report.html"
        return Template(template.read_text(encoding="utf-8")).substitute(
            lang=escape(data["lang"]), title=escape(data["title"]), overview=html_text(data["overview"]),
            reading=self.html_reading(), tree=escape(self.label("tree")), seed_label=self.label("seed"),
            seed_id=seed["id"], seed_title=escape(seed.get("label") or seed["title"]),
            seed_paper=seed_paper, group_map=group_map, groups=groups,
            clues_label=self.label("clues"), clues=self.html_notes(data["clues"]),
            coverage_label=self.label("coverage"), coverage=self.html_notes(data["coverage"]),
            md_file=quote(self.filename, safe="") + ".md", md_label=self.label("markdown"),
        )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--name", required=True)
    args = parser.parse_args()
    if not args.name.strip() or any(c in args.name for c in '<>:"/\\|?*\x00') or args.name.endswith((".", " ")):
        parser.error("--name must be a filename prefix")
    try:
        report = Report(json.loads(args.input.read_text(encoding="utf-8-sig")), args.name)
        markdown, html = report.markdown(), report.html()
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(str(error))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / f"{args.name}.md").write_text(markdown, encoding="utf-8")
    (args.output_dir / f"{args.name}.html").write_text(html, encoding="utf-8")


if __name__ == "__main__":
    main()
