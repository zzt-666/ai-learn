# 衰衰闯关

任意知识闯关学习助手 · Phase 0  
微信小程序（Taro 4 + React 18 + TS）+ FastAPI + LangChain + DeepSeek

## 目录

- `backend/` Python 后端
- `frontend/` Taro 微信小程序前端
- `docs/` 需求与方案
- `UI原型/` 视觉与流程原型

## 后端

```bash
cd backend
# Windows 可用已创建的 .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

# 确认 .env 中已填写 DEEPSEEK_API_KEY
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

测试（TDD）：

```bash
cd backend
.\.venv\Scripts\python.exe -m pytest -q
```

## 前端

```bash
cd frontend
npm install
npm run dev:weapp
```

用微信开发者工具打开 `frontend/dist`，并勾选「不校验合法域名」。  
开发期 API 默认：`http://127.0.0.1:8000`

## Phase 0 范围

主路径逻辑：粘贴文本 → AI 出题 → 单选/多选/判断闯关 → 讲解 → 报告。  
仅 UI：TabBar 题库/我的、积分 EXP、快捷选题、未完成列表、海报分享。  
无登录、无倒计时、无续玩真逻辑。
