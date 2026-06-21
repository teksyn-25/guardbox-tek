import 'dart:convert';
import 'dart:typed_data';

import 'package:http/http.dart' as http;

import '../models/file_item.dart';

class ApiException implements Exception {
  final int statusCode;
  final String message;

  const ApiException(this.statusCode, this.message);

  @override
  String toString() => 'ApiException($statusCode): $message';
}

class ApiClient {
  final String baseUrl;
  final String token;
  final http.Client _http;

  ApiClient({
    required this.baseUrl,
    required this.token,
    http.Client? httpClient,
  }) : _http = httpClient ?? http.Client();

  Map<String, String> get _headers => {
        'Authorization': 'Bearer $token',
        'Content-Type': 'application/json',
      };

  Future<List<FileItem>> listFiles(String state) async {
    final uri = Uri.parse('$baseUrl/api/files?state=$state');
    final res = await _http.get(uri, headers: _headers);
    _check(res);
    final list = jsonDecode(res.body) as List;
    return list
        .map((j) => FileItem.fromJson(j as Map<String, dynamic>, state: state))
        .toList();
  }

  Future<FileItem> getMetadata(String fileId, {String state = 'pending'}) async {
    final uri = Uri.parse('$baseUrl/api/files/$fileId');
    final res = await _http.get(uri, headers: _headers);
    _check(res);
    return FileItem.fromJson(
      jsonDecode(res.body) as Map<String, dynamic>,
      state: state,
    );
  }

  Future<Uint8List> getImage(String fileId) async {
    final uri = Uri.parse('$baseUrl/api/files/$fileId/image');
    final res = await _http.get(uri, headers: {'Authorization': 'Bearer $token'});
    _check(res);
    return res.bodyBytes;
  }

  Future<void> saveFile(String fileId) async {
    final uri = Uri.parse('$baseUrl/api/files/$fileId/save');
    final res = await _http.post(uri, headers: _headers);
    _check(res);
  }

  Future<void> deleteFile(String fileId) async {
    final uri = Uri.parse('$baseUrl/api/files/$fileId');
    final res = await _http.delete(uri, headers: _headers);
    _check(res);
  }

  Future<String> uploadFile(Uint8List bytes) async {
    final uri = Uri.parse('$baseUrl/api/files/upload');
    final req = http.MultipartRequest('POST', uri)
      ..headers['Authorization'] = 'Bearer $token'
      ..files.add(http.MultipartFile.fromBytes('file', bytes));
    final streamed = await _http.send(req);
    final res = await http.Response.fromStream(streamed);
    _check(res);
    final json = jsonDecode(res.body) as Map<String, dynamic>;
    return json['file_id'] as String;
  }

  void _check(http.Response res) {
    if (res.statusCode >= 200 && res.statusCode < 300) return;
    throw ApiException(res.statusCode, res.body);
  }

  void dispose() => _http.close();
}
