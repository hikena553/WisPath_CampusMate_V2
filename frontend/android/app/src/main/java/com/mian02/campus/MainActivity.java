
package com.mian02.campus;

import android.os.Build;
import android.os.Bundle;
import android.view.ViewGroup;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.Plugin;

/**
 * Android 返回键 / 全面屏侧滑返回处理。
 *
 * 背景：Android 13+（尤其 Android 15/16 上 targetSdk 35 的应用）系统会把返回手势
 * 交给 OnBackInvokedCallback，而不再调用 onBackPressed。部分定制 ROM（vivo OriginOS）
 * 在预测性返回链路里不会把事件转给 Capacitor 的 JS 桥，导致「一滑就整机退出」。
 *
 * 做法：不依赖 JS 桥，直接在原生层注册返回回调：
 * - WebView 还能回退（含前端 useBackLayer 压入的页内浮层哨兵）→ goBack() 逐级返回；
 * - 已在一级页面 → moveTaskToBack(true) 退到后台，不杀进程、不丢登录态。
 *
 * 同时保留 onBackPressed 覆盖，兼容未启用预测性返回的旧系统 / 旧设备。
 * Capacitor App 插件自身的返回处理已在 capacitor.config 中关闭（disableBackButtonHandler），
 * 避免与这里重复触发。
 *
 * 另外：Android 15/16 上 targetSdk 35 的应用是强制 edge-to-edge，系统不再替我们
 * resize 窗口，默认还会把整个窗口上推（adjustPan）——聊天页输入时页头会被顶出屏幕。
 * 这里改为自己处理 IME insets：按键盘高度给 WebView 加底部 margin，等价于「窗口缩到键盘上方」，
 * 页面侧看到的是 viewport 变矮，fixed 顶栏/输入栏都能正常让位。
 */
public class MainActivity extends BridgeActivity {

    private OnBackInvokedCallback backCallback;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // QQ 互联移动端授权插件：官方 SDK aar（android/app/libs/）就位后才会编译进包，
        // 未就位时这里按缺失处理跳过注册，QQ 授权入口在网页侧自动回退。
        try {
            @SuppressWarnings("unchecked")
            Class<? extends Plugin> qqPlugin =
                    (Class<? extends Plugin>) Class.forName("com.mian02.campus.QQAuthPlugin");
            registerPlugin(qqPlugin);
        } catch (ClassNotFoundException ignored) {
            // libs 里还没有 QQ OpenSDK aar：不注册插件，其余功能不受影响
        }

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            backCallback = this::handleBack;
            OnBackInvokedDispatcher dispatcher = getOnBackInvokedDispatcher();
            dispatcher.registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_OVERLAY, backCallback);
        }

        // 软键盘：把 WebView 缩到 IME 上方，等价于旧系统的 adjustResize
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(android.R.id.content), (v, insets) -> {
            int kb = insets.getInsets(WindowInsetsCompat.Type.ime()).bottom;
            if (getBridge() != null && getBridge().getWebView() != null) {
                android.webkit.WebView wv = getBridge().getWebView();
                ViewGroup.LayoutParams lp = wv.getLayoutParams();
                if (lp instanceof ViewGroup.MarginLayoutParams) {
                    ViewGroup.MarginLayoutParams mlp = (ViewGroup.MarginLayoutParams) lp;
                    if (mlp.bottomMargin != kb) {
                        mlp.bottomMargin = kb;
                        wv.setLayoutParams(mlp);
                    }
                }
            }
            return insets;
        });
    }

    /**
     * 前端登记的「页内浮层返回入口」（见 src/composables/useBackLayer.ts）。
     * 页面返回 true = 已经收掉一层，原生不要再退历史、更不要退后台。
     */
    private static final String JS_HANDLE_BACK =
            "(function(){try{var f=window.__mian02HandleBack;"
                    + "return (typeof f === 'function' && f() === true);}catch(e){return false;}})()";

    /**
     * 返回键真正的落点。
     *
     * 不能只看 canGoBack()：聊天窗口 / 帖子详情 / 个人中心子页这类「页内浮层」是靠
     * 前端在历史顶部压一条同地址哨兵间接进历史的，哨兵一旦被路由 replace 吃掉，
     * 或者页面本来就是历史第一条（从通知 / 深链直接落到聊天），canGoBack() 就是 false。
     * 旧逻辑这时直接 moveTaskToBack()，用户看到的就是「在聊天里侧滑，App 直接回桌面」。
     *
     * 现在的顺序：
     *   ① 先问页面：有没有页内浮层要收（有就收一层，原生什么都不做）；
     *   ② 没有浮层但有 WebView 历史 -> goBack()，交给路由一级一级退；
     *   ③ 都没有（已在一级页面）-> moveTaskToBack()，退到后台但不杀进程。
     */
    private void handleBack() {
        if (getBridge() == null || getBridge().getWebView() == null) {
            moveTaskToBack(true);
            return;
        }
        final android.webkit.WebView wv = getBridge().getWebView();
        wv.evaluateJavascript(JS_HANDLE_BACK, value -> {
            if ("true".equals(value)) {
                return;
            }
            if (wv.canGoBack()) {
                wv.goBack();
            } else {
                moveTaskToBack(true);
            }
        });
    }

    @SuppressWarnings("deprecation")
    @Override
    public void onBackPressed() {
        handleBack();
    }
}
