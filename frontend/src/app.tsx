import { PropsWithChildren, useEffect } from 'react'
import { ensureLogin } from './utils/auth'
import './app.scss'

function App({ children }: PropsWithChildren) {
  useEffect(() => {
    ensureLogin().catch(() => {
      // 首页会展示登录失败与重试
    })
  }, [])

  return children
}

export default App
