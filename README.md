# IRASUTOYAget

一个 Claude Code 技能（Skill），从日本免费插画网站 [IRASUTOYA（いらすとや）](https://www.irasutoya.com/) 搜索并下载可爱插图。

## 功能

- 🔍 自动将中/英文关键词翻译成日语进行搜索
- 🖼️ 从 IRASUTOYA 搜索结果中提取高清原图
- 📥 一键下载插图到本地
- 🎯 智能匹配最相关的插图

## 安装

### 前置条件

- Python 3.10+
- `requests` 和 `beautifulsoup4`

```bash
pip install requests beautifulsoup4
```

### 方式一：下载 .skill 文件安装（推荐）

1. 从 [Releases](https://github.com/LunTr/IRASUTOYAget/releases) 下载最新的 `IRASUTOYAget.skill` 文件
2. 将文件放到 Claude 的 skills 目录：

```bash
# Windows
copy IRASUTOYAget.skill %USERPROFILE%\.claude\skills\

# macOS / Linux
cp IRASUTOYAget.skill ~/.claude/skills/
```

3. 重启 Claude Code，技能自动生效

### 方式二：克隆仓库安装

```bash
# Windows
git clone https://github.com/LunTr/IRASUTOYAget.git %USERPROFILE%\.claude\skills\IRASUTOYAget

# macOS / Linux
git clone https://github.com/LunTr/IRASUTOYAget.git ~/.claude/skills/IRASUTOYAget
```

### 方式三：项目内使用

将仓库克隆到你的项目目录中，Claude 会自动识别项目内的 `.claude/skills/` 下的技能：

```bash
cd your-project
git clone https://github.com/LunTr/IRASUTOYAget.git .claude/skills/IRASUTOYAget
```

### 验证安装

在 Claude Code 中输入 `/IRASUTOYAget`，如果出现技能说明则安装成功。

## 使用方法

### 自然语言触发

直接用中文或英文告诉 Claude 你想要什么插图：

```
帮我找一张猫的插图
I need a cute illustration of a dog
找几张商务会议的配图
```

### 指令触发

```
/IRASUTOYAget 下载一份含有雪碧和冰棍的插图
```

## 工作原理

1. **关键词翻译**：将用户输入翻译成日语（IRASUTOYA 是日文网站）
2. **搜索**：通过 `scripts/search_irasutoya.py` 脚本搜索 IRASUTOYA
3. **解析**：解析搜索结果页面的 JavaScript 动态内容，提取缩略图和标题
4. **获取原图**：访问详情页，通过 `og:image` 元标签获取高清原图 URL
5. **下载**：保存图片到本地

## 脚本独立使用

也可以脱离 Claude 直接使用脚本：

```bash
# 搜索（不下载）
python scripts/search_irasutoya.py "猫" --list-only --json --limit 10

# 搜索并下载第 1 个结果
python scripts/search_irasutoya.py "猫" --output ./output --index 0

# 下载第 3 个结果
python scripts/search_irasutoya.py "犬" --output ./images --index 2
```

### 参数

| 参数 | 说明 |
|------|------|
| `keyword` | 搜索关键词（日语） |
| `--output, -o` | 输出目录（默认当前目录） |
| `--limit, -l` | 最大搜索结果数（默认 10） |
| `--list-only` | 只列出结果，不下载 |
| `--index, -i` | 下载指定序号的结果（从 0 开始） |
| `--json` | 以 JSON 格式输出结果 |

## 目录结构

```
IRASUTOYAget/
├── SKILL.md                    # 技能定义文件
├── README.md                   # 本文件
├── requirements.txt            # Python 依赖
├── scripts/
│   └── search_irasutoya.py     # 搜索下载脚本
├── evals/
│   └── evals.json              # 测试用例
└── output/                     # 下载的插图示例
```

## 示例输出

```
搜索 IRASUTOYA：猫
找到 10 个结果：

  [0] いろいろな模様の猫のイラスト
  [1] いろいろな濡れて細くなった猫のイラスト
  [2] いろいろな猫の手のイラスト

下载：いろいろな模様の猫のイラスト
  -> ./output/いろいろな模様の猫のイラスト.jpg
```

## 注意事项

- IRASUTOYA 的插图可以免费用于个人和商业用途，但请勿大批量下载或再分发
- 搜索脚本在请求之间有 0.5 秒延迟，以尊重服务器
- 图片格式取决于源文件，通常为 JPG 或 PNG

## License

MIT
