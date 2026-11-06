package com.mian02.campus;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;

import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

import com.tencent.connect.common.Constants;
import com.tencent.tauth.IUiListener;
import com.tencent.tauth.Tencent;
import com.tencent.tauth.UiError;

import org.json.JSONObject;

/**
 * QQ 互联移动端授权插件（官方 OpenSDK）。
 *
 * 编译依赖 android/app/libs/ 下的官方 open_sdk_*.aar；aar 未就位时本文件会被
 * build.gradle 的 sourceSets 剔除、MainActivity 的条件注册自动跳过，
 * 壳工程其余功能不受影响。
 *
 * 前端入口见 src/utils/qqAuth.ts：login 返回 { openId, accessToken, expiresIn }，
 * 由网页侧调 /api/auth/qq/mobile/* 完成服务端核验（本插件不直接接触后端）。
 */
@CapacitorPlugin(name = "QQAuth")
public class QQAuthPlugin extends Plugin {

    private Tencent tencent;
    private PluginCall pendingCall;
    private IUiListener loginListener;

    private String appId() {
        try {
            return getBridge().getContext().getString(
                    getBridge().getContext().getResources().getIdentifier(
                            "qq_app_id", "string", getBridge().getContext().getPackageName()));
        } catch (Exception e) {
            return "";
        }
    }

    private Tencent tencent() {
        if (tencent != null) return tencent;
        String appId = appId();
        if (appId.isEmpty()) return null;
        Context context = getBridge().getContext();
        try {
            // OpenSDK 3.5+：FileProvider authority 用于授权缓存，与壳工程已配置的 provider 一致
            tencent = Tencent.createInstance(appId, context, context.getPackageName() + ".fileprovider");
        } catch (NoSuchMethodError e) {
            // 旧版 SDK 只有双参重载
            tencent = Tencent.createInstance(appId, context);
        }
        return tencent;
    }

    @PluginMethod
    public void isQQInstalled(PluginCall call) {
        Tencent t = tencent();
        if (t == null) {
            call.reject("QQ_NOT_CONFIGURED", "QQ_APP_ID 未配置");
            return;
        }
        JSObject ret = new JSObject();
        try {
            ret.put("installed", t.isQQInstalled(getBridge().getContext()));
        } catch (Exception e) {
            ret.put("installed", false);
        }
        call.resolve(ret);
    }

    @PluginMethod
    public void login(PluginCall call) {
        Tencent t = tencent();
        if (t == null) {
            call.reject("QQ_NOT_CONFIGURED", "QQ_APP_ID 未配置");
            return;
        }
        Activity activity = getActivity();
        if (activity == null) {
            call.reject("QQ_ERROR", "Activity 不可用");
            return;
        }
        try {
            if (!t.isQQInstalled(activity)) {
                call.reject("QQ_NOT_INSTALLED", "未检测到手机 QQ");
                return;
            }
        } catch (Exception e) {
            // 包可见性异常等情况按未安装处理
            call.reject("QQ_NOT_INSTALLED", "未检测到手机 QQ");
            return;
        }
        if (pendingCall != null) {
            // 上一次授权未回（如中途切走），先释放再发起新的授权
            pendingCall.reject("QQ_LOGIN_BUSY", "上一次 QQ 授权未完成，请重试");
        }
        pendingCall = call;
        String scope = call.getString("scope", "all");
        loginListener = new IUiListener() {
            // 兼容新旧两代 OpenSDK 的 onComplete 签名（3.5.x 起参数放宽为 Object）
            public void onComplete(Object response) {
                finishLogin(response);
            }

            public void onComplete(JSONObject response) {
                finishLogin(response);
            }

            public void onError(UiError error) {
                rejectPending("QQ_ERROR", error != null ? error.errorMessage : "QQ 授权失败");
            }

            public void onCancel() {
                rejectPending("USER_CANCEL", "已取消 QQ 授权");
            }

            public void onWarning(int code) {
                // SDK 偶发非致命告警，等待后续回调即可
            }
        };
        t.login(activity, scope, loginListener);
    }

    /** 解析授权回包：ret=0 时取 openId / access_token / expires_in 回给网页侧 */
    private void finishLogin(Object response) {
        PluginCall call = pendingCall;
        clearPending();
        if (call == null) return;
        try {
            JSONObject json = response instanceof JSONObject
                    ? (JSONObject) response
                    : new JSONObject(String.valueOf(response));
            int ret = json.optInt("ret", -1);
            if (ret != 0) {
                call.reject("QQ_ERROR", json.optString("msg", "QQ 授权失败"));
                return;
            }
            String openId = json.optString("openId", json.optString("openid", ""));
            String accessToken = json.optString("access_token", "");
            long expiresIn = json.optLong("expires_in", 0);
            if (openId.isEmpty() || accessToken.isEmpty()) {
                call.reject("QQ_ERROR", "QQ 授权回包缺少 openId/access_token");
                return;
            }
            JSObject result = new JSObject();
            result.put("openId", openId);
            result.put("accessToken", accessToken);
            result.put("expiresIn", expiresIn);
            call.resolve(result);
        } catch (Exception e) {
            call.reject("QQ_ERROR", "QQ 授权回包解析失败");
        }
    }

    private void rejectPending(String code, String message) {
        PluginCall call = pendingCall;
        clearPending();
        if (call != null) call.reject(code, message);
    }

    private void clearPending() {
        pendingCall = null;
        loginListener = null;
    }

    @PluginMethod
    public void logout(PluginCall call) {
        Tencent t = tencent();
        if (t != null) {
            try {
                t.logout(getBridge().getContext());
            } catch (Exception ignored) {
                // 登出失败不影响网页侧登录态
            }
        }
        call.resolve();
    }

    /** QQ 客户端授权结果经 AuthActivity 转回，必须转发给 SDK 才会触发 IUiListener */
    @Override
    protected void handleOnActivityResult(int requestCode, int resultCode, Intent data) {
        super.handleOnActivityResult(requestCode, resultCode, data);
        if (requestCode == Constants.REQUEST_LOGIN && loginListener != null) {
            Tencent.onActivityResultData(requestCode, resultCode, data, loginListener);
            // 结果异常中断（ resultCode != OK 且 SDK 不回调）时，避免 pendingCall 悬挂
            if (pendingCall != null && resultCode != Activity.RESULT_OK) {
                rejectPending("QQ_ERROR", "QQ 授权未完成，请重试");
            }
        }
    }
}
