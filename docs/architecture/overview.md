# 架构概览

系统采用命令—事件—状态投影模型。纯 Python 引擎接收经过校验的命令，读取结构化规则并产生带规则出处的事件；SQLite、FastAPI、Web UI、LLM 与未来 RL 适配器均依赖这一接口。

```text
Web / LLM / RL
      |
observe + legal_actions + commands
      |
FastAPI / in-process adapter
      |
deterministic engine -> rule events -> SQLite/replay
      |
structured YAML/CSV + source audit
```

地图背景仅用于显示。坐标、邻接、地形、可见性和合法移动由结构化数据决定。
