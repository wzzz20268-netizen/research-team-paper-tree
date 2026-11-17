# 检索与证据来源

## 优先查什么

| 对象 | 首选证据 | 补查方式 |
| --- | --- | --- |
| 原论文与通讯身份 | 发表页、PDF 的署名脚注或 correspondence、论文明确的通讯作者段落 | DOI 元数据核实论文身份；OpenAlex 的 authorship 标记作线索。联系邮箱或事实上的作者顺序不足以单独确认。 |
| 人与研究组 | 论文当年的具体组署名、机构的历史教师页、实验室成员与发表页、带日期的简历或公开项目记录 | ORCID 用于作者消歧，按任职年份对照。组名可用原文和缩写分别搜。 |
| 论文候选 | 组发表清单、[OpenAlex 作者记录](https://help.openalex.org/data/authors/)、[OpenAlex 论文索引](https://help.openalex.org/data/works/) | 按领域用 [DBLP](https://dblp.org/)、[arXiv](https://arxiv.org/)、[PubMed](https://pubmed.ncbi.nlm.nih.gov/) 或对应学会和机构库。可访问时补查本地语言和地区索引。利用引用网络，核对索引遗漏和标错的作者。 |
| 版本与发布日期 | DOI 落地页、会议论文集、预印本历史、出版方的版本说明 | [Crossref 的预印本版本关系](https://www.crossref.org/documentation/research-nexus/posted-content-includes-preprints/) 可进行双向查验。缺失关系字段时继续查来源页面。 |
| 团队事实及资助 | 组／机构官网、资助机构项目公示、资助编号、论文致谢 | 一个项目可能共同资助多组。区分项目负责人、参与单位、作者个人获奖和仅出现在致谢中的基金编号。 |

## 扩展搜索

- 用 DOI 定位种子论文。用 ORCID 或已核实的索引 ID 枚举通讯作者成果，再查与方向相关、且有在组证据的其他成员同期成果。OpenAlex 的 [API 查询示例](https://help.openalex.org/how-to/api-recipes/) 包含作者筛选、引用和游标分页。按可用工具和数据库访问条件使用 API 或网页。API 不可用时，优先查官方发表清单、可访问的作者目录和学科索引，并记下覆盖差异。
- 将组名、负责人和成员名字分别同核心问题词、方法词、对象词组合。分开搜「同问题＋其他方法」和「同方法＋其他问题」。按需要换用早期术语、拼写、汉字和转写。共作者、引用和基金编号可用于发现新候选，仍需逐篇核对。
- 保存足以复核的检索轨迹：来源、日期、查询式或目录地址、检索的年段、是否读完及限制。必要时按团队记录候选、已收录、待核实、已排除及其原因。把索引列表的完整程度与实际组成果的完整程度分别描述。

## 设计参考

检索覆盖和版本归并参考了 [K-Dense 的 Literature Review Skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/ec59a29a03d5c40f73ab40878df04860bc00e876/skills/literature-review/SKILL.md) 的筛选与核验方法。
