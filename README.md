# Trae 技能仓库

存放团队内部可复用的 Trae 技能，安装后在任意项目直接触发。

## 技能列表

| 技能 | 用途 |
|---|---|
| [trademark-pass-rate](trademark-pass-rate/SKILL.md) | 商标注册通过率评估，输出单页 HTML 与 PDF |

## 安装方式

在 Trae 里直接说：

> 安装技能：https://github.com/<用户名>/trae-skills/tree/main/trademark-pass-rate

或者手动安装：把 `trademark-pass-rate` 整个文件夹复制到

```
C:\Users\<你的用户名>\.trae-cn\skills\
```

重启 Trae 后生效。

## 使用

安装完成后直接输入：

> 帮我查：企思妙想商标的注册通过率

技能会依次完成：补齐公司名称与商标类别、检查 OA-MCP 是否可用、四轮近似检索、分层评估、输出 HTML 与 PDF。

## 依赖

- OA-MCP 商标基础索引接口（`es_trademark_base_search`），数据范围需经理及以上
- 本机安装 Chrome 或 Edge，用于把 HTML 打印成 PDF
- Python 3.8 及以上，无需第三方库
