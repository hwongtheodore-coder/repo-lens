# RepoLens

一个探索公开 GitHub 仓库的 AI 问答原型。输入仓库地址和问题，程序选取部分代码文件，生成回答并列出参考文件。

## 运行

需要 Python 3.9 或更高版本。PowerShell 中：

```powershell
cd repo-lens
$env:OPENAI_API_KEY="你的 API Key"
python app.py
```

访问 http://127.0.0.1:8000。可选设置 `OPENAI_MODEL`；未设置 API Key 时仍能检索文件，但不会生成 AI 回答。API 调用可能产生费用。

## 当前限制

- 仅支持公开仓库；GitHub 未认证请求有速率限制。
- 根据问题中的词对文件路径排序，最多读取前 8 个文件，不能保证召回相关代码；引用为文件级别，不含行号。
- 代码会发送给模型服务；只适合可以发送到外部服务的公开内容。
- 架构图、补丁生成、评测和完整代码索引尚未实现。

