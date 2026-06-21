import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:shared_preferences/shared_preferences.dart';

const _keyServerUrl = 'server_url';
const _keyToken = 'gb_token';

const _secure = FlutterSecureStorage();

Future<String?> getServerUrl() async {
  final prefs = await SharedPreferences.getInstance();
  return prefs.getString(_keyServerUrl);
}

Future<void> setServerUrl(String url) async {
  final prefs = await SharedPreferences.getInstance();
  await prefs.setString(_keyServerUrl, url.replaceAll(RegExp(r'/+$'), ''));
}

Future<String?> getToken() async => _secure.read(key: _keyToken);

Future<void> setToken(String token) async =>
    _secure.write(key: _keyToken, value: token);

Future<void> clearToken() async => _secure.delete(key: _keyToken);
