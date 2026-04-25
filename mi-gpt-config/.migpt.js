// mi-gpt 配置文件
// 文档: https://github.com/idootop/mi-gpt/blob/main/docs/settings.md

export default {
  // 系统 Prompt - 让龙虾用你喜欢的风格回答
  systemPrompt: `你是小爱同学，一个智能语音助手。请用简洁、自然的中文回答用户的问题。
回答要口语化，适合语音播报，不要太长。`,

  // 是否启用连续对话（L05B 不支持，保持 false）
  streamResponse: false,

  // 唤醒后多久不说话自动退出（秒）
  exitKeepAliveAfter: 30,

  // 回答的最大长度（字符数，语音不宜太长）
  maxTokens: 500,
}
