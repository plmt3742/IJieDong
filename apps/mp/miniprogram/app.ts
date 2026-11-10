import { getApiBaseUrl, APP_NAME, APP_VERSION, DEMO_MODE } from './services/config';

App<IAppOption>({
  globalData: {
    apiBaseUrl: '',
    appName: APP_NAME,
    version: APP_VERSION,
    demoMode: DEMO_MODE,
    systemInfo: null,
  },

  onLaunch() {
    this.globalData.apiBaseUrl = getApiBaseUrl();
    try {
      this.globalData.systemInfo = wx.getSystemInfoSync();
    } catch (error) {
      this.globalData.systemInfo = null;
      console.warn('[app] unable to read system info', error);
    }
  },

  onError(message: string) {
    console.error('[app] runtime error', message);
  },
});
