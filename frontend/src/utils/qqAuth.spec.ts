import { beforeEach, describe, expect, it, vi } from 'vitest'

const qqMock = vi.hoisted(() => ({
  native: false,
  plugin: false,
  login: vi.fn(),
}))

vi.mock('@capacitor/core', () => ({
  Capacitor: {
    isNativePlatform: () => qqMock.native,
    isPluginAvailable: () => qqMock.plugin,
  },
  registerPlugin: () => ({
    login: qqMock.login,
    isQQInstalled: vi.fn(),
    logout: vi.fn(),
  }),
}))

import {
  QqNativeError,
  normalizeQqNativeError,
  qqNativeAuthAvailable,
  qqNativeErrorCode,
  qqNativeErrorMessage,
  qqNativeLogin,
} from './qqAuth'

describe('qqNativeAuthAvailable', () => {
  beforeEach(() => {
    qqMock.native = false
    qqMock.plugin = false
    qqMock.login.mockReset()
  })

  it('浏览器环境不可用', () => {
    expect(qqNativeAuthAvailable()).toBe(false)
  })

  it('原生壳但未注册插件（缺 OpenSDK aar）时不可用', () => {
    qqMock.native = true
    expect(qqNativeAuthAvailable()).toBe(false)
  })

  it('原生壳且插件已注册时可用', () => {
    qqMock.native = true
    qqMock.plugin = true
    expect(qqNativeAuthAvailable()).toBe(true)
  })
})

describe('qqNativeLogin', () => {
  beforeEach(() => {
    qqMock.native = false
    qqMock.plugin = false
    qqMock.login.mockReset()
  })

  it('插件缺失时抛 QQ_PLUGIN_MISSING，而不是笼统的登录失败', async () => {
    qqMock.native = true
    await expect(qqNativeLogin()).rejects.toMatchObject({ code: 'QQ_PLUGIN_MISSING' })
  })

  it('透传原生授权结果', async () => {
    qqMock.native = true
    qqMock.plugin = true
    const session = { openId: 'oid', accessToken: 'tok', expiresIn: 90 }
    qqMock.login.mockResolvedValue(session)
    await expect(qqNativeLogin()).resolves.toEqual(session)
    expect(qqMock.login).toHaveBeenCalledWith({ scope: 'all' })
  })

  it('把插件拒绝码归一成 QqNativeError', async () => {
    qqMock.native = true
    qqMock.plugin = true
    qqMock.login.mockRejectedValue(Object.assign(new Error('已取消 QQ 授权'), { code: 'USER_CANCEL' }))
    await expect(qqNativeLogin()).rejects.toMatchObject({ code: 'USER_CANCEL' })
  })
})

describe('normalizeQqNativeError', () => {
  it('把 Capacitor UNIMPLEMENTED 识别为插件未集成', () => {
    const error = new Error('"QQAuth.login()" is not implemented on android')
    expect(normalizeQqNativeError(error).code).toBe('QQ_PLUGIN_MISSING')
    expect(qqNativeErrorMessage(error)).toContain('未集成 QQ 登录组件')
  })

  it('保留插件拒绝码', () => {
    expect(qqNativeErrorCode(Object.assign(new Error('x'), { code: 'QQ_NOT_INSTALLED' }))).toBe('QQ_NOT_INSTALLED')
  })

  it('未知异常归为 UNKNOWN 并使用兜底文案', () => {
    const error = new Error('boom')
    expect(qqNativeErrorCode(error)).toBe('UNKNOWN')
    expect(qqNativeErrorMessage(error, 'QQ 授权失败，请重试')).toBe('QQ 授权失败，请重试')
  })
})

describe('qqNativeErrorMessage', () => {
  it('用户取消返回空串（调用方静默）', () => {
    expect(qqNativeErrorMessage(new QqNativeError('USER_CANCEL'))).toBe('')
  })

  it('未安装 QQ 给出安装引导', () => {
    expect(qqNativeErrorMessage(new QqNativeError('QQ_NOT_INSTALLED'))).toContain('请安装后重试')
  })
})
