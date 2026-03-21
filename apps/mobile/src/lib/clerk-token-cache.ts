import * as SecureStore from "expo-secure-store";

export const tokenCache = {
  async clearToken(key: string) {
    await SecureStore.deleteItemAsync(key);
  },
  async getToken(key: string) {
    return SecureStore.getItemAsync(key);
  },
  async saveToken(key: string, value: string) {
    await SecureStore.setItemAsync(key, value);
  }
};

