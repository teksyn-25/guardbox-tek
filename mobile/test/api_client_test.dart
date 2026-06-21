import 'dart:convert';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:mocktail/mocktail.dart';

import 'package:guardbox/services/api_client.dart';

class _MockHttp extends Mock implements http.Client {}
class _FakeUri extends Fake implements Uri {}
class _FakeRequest extends Fake implements http.BaseRequest {}

const _base = 'https://guardbox.example.com';
const _token = 'tok-abc123';

const _fileJson = <String, dynamic>{
  'file_id': 'f1',
  'source': 'telegram_bot',
  'source_format': 'jpeg',
  'stripped': ['exif'],
  'output_format': 'png',
  'dimensions': {'width': 400, 'height': 300},
};

http.Response _ok(Object body) =>
    http.Response(jsonEncode(body), 200);

void main() {
  late _MockHttp mockHttp;
  late ApiClient client;

  setUpAll(() {
    registerFallbackValue(_FakeUri());
    registerFallbackValue(_FakeRequest());
  });

  setUp(() {
    mockHttp = _MockHttp();
    client = ApiClient(baseUrl: _base, token: _token, httpClient: mockHttp);
  });

  // ── listFiles ─────────────────────────────────────────────────────────────

  group('listFiles', () {
    void stubGet(Object body, {int status = 200}) {
      when(() => mockHttp.get(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response(jsonEncode(body), status));
    }

    test('calls GET /api/files?state=pending', () async {
      stubGet([_fileJson]);
      await client.listFiles('pending');

      final uri = verify(() =>
              mockHttp.get(captureAny(), headers: any(named: 'headers')))
          .captured
          .first as Uri;
      expect(uri.toString(), '$_base/api/files?state=pending');
    });

    test('calls GET /api/files?state=saved', () async {
      stubGet([_fileJson]);
      await client.listFiles('saved');

      final uri = verify(() =>
              mockHttp.get(captureAny(), headers: any(named: 'headers')))
          .captured
          .first as Uri;
      expect(uri.toString(), '$_base/api/files?state=saved');
    });

    test('includes Bearer token in Authorization header', () async {
      stubGet([_fileJson]);
      await client.listFiles('pending');

      final headers = verify(() =>
              mockHttp.get(any(), headers: captureAny(named: 'headers')))
          .captured
          .first as Map<String, String>;
      expect(headers['Authorization'], 'Bearer $_token');
    });

    test('returns parsed FileItem list', () async {
      stubGet([_fileJson, _fileJson]);
      final files = await client.listFiles('pending');
      expect(files, hasLength(2));
      expect(files.first.fileId, 'f1');
      expect(files.first.state, 'pending');
    });

    test('returns empty list for empty response', () async {
      stubGet([]);
      final files = await client.listFiles('pending');
      expect(files, isEmpty);
    });

    test('throws ApiException on 401', () async {
      stubGet('Unauthorized', status: 401);
      expect(() => client.listFiles('pending'), throwsA(isA<ApiException>()));
    });

    test('throws ApiException on 500', () async {
      stubGet('Internal server error', status: 500);
      expect(() => client.listFiles('pending'), throwsA(isA<ApiException>()));
    });
  });

  // ── getImage ──────────────────────────────────────────────────────────────

  group('getImage', () {
    test('calls GET /api/files/{id}/image', () async {
      when(() => mockHttp.get(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response.bytes(Uint8List(4), 200));

      await client.getImage('f1');

      final uri = verify(() =>
              mockHttp.get(captureAny(), headers: any(named: 'headers')))
          .captured
          .first as Uri;
      expect(uri.toString(), '$_base/api/files/f1/image');
    });

    test('returns raw PNG bytes', () async {
      final expected = Uint8List.fromList([137, 80, 78, 71]); // PNG magic bytes
      when(() => mockHttp.get(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response.bytes(expected, 200));

      final bytes = await client.getImage('f1');
      expect(bytes, expected);
    });

    test('throws ApiException on 404', () async {
      when(() => mockHttp.get(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response.bytes(Uint8List(0), 404));
      expect(() => client.getImage('f1'), throwsA(isA<ApiException>()));
    });
  });

  // ── saveFile ──────────────────────────────────────────────────────────────

  group('saveFile', () {
    test('calls POST /api/files/{id}/save', () async {
      when(() => mockHttp.post(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response('', 204));

      await client.saveFile('f1');

      final uri = verify(() =>
              mockHttp.post(captureAny(), headers: any(named: 'headers')))
          .captured
          .first as Uri;
      expect(uri.toString(), '$_base/api/files/f1/save');
    });

    test('throws ApiException on 404', () async {
      when(() => mockHttp.post(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response('', 404));
      expect(() => client.saveFile('missing'), throwsA(isA<ApiException>()));
    });
  });

  // ── deleteFile ────────────────────────────────────────────────────────────

  group('deleteFile', () {
    test('calls DELETE /api/files/{id}', () async {
      when(() => mockHttp.delete(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response('', 204));

      await client.deleteFile('f1');

      final uri = verify(() =>
              mockHttp.delete(captureAny(), headers: any(named: 'headers')))
          .captured
          .first as Uri;
      expect(uri.toString(), '$_base/api/files/f1');
    });

    test('throws ApiException on 404', () async {
      when(() => mockHttp.delete(any(), headers: any(named: 'headers')))
          .thenAnswer((_) async => http.Response('', 404));
      expect(() => client.deleteFile('missing'), throwsA(isA<ApiException>()));
    });
  });

  // ── uploadFile ────────────────────────────────────────────────────────────

  group('uploadFile', () {
    void stubSend({int status = 201, String body = '{"file_id":"new-id"}'}) {
      when(() => mockHttp.send(any())).thenAnswer((_) async =>
          http.StreamedResponse(Stream.value(utf8.encode(body)), status));
    }

    test('calls POST /api/files/upload', () async {
      stubSend();
      await client.uploadFile(Uint8List.fromList([1, 2, 3]));

      final req = verify(() => mockHttp.send(captureAny())).captured.first
          as http.MultipartRequest;
      expect(req.url.toString(), '$_base/api/files/upload');
      expect(req.method, 'POST');
    });

    test('does not include original filename in multipart — privacy rule', () async {
      stubSend();
      await client.uploadFile(Uint8List.fromList([1, 2, 3]));

      final req = verify(() => mockHttp.send(captureAny())).captured.first
          as http.MultipartRequest;
      expect(req.files.first.filename, isNull,
          reason: 'Original filename must never be transmitted — see CLAUDE.md metadata rules');
    });

    test('includes Bearer token in Authorization header', () async {
      stubSend();
      await client.uploadFile(Uint8List.fromList([1, 2, 3]));

      final req = verify(() => mockHttp.send(captureAny())).captured.first
          as http.MultipartRequest;
      expect(req.headers['Authorization'], 'Bearer $_token');
    });

    test('returns file_id from response', () async {
      stubSend(body: '{"file_id":"returned-id"}');
      final id = await client.uploadFile(Uint8List.fromList([1, 2, 3]));
      expect(id, 'returned-id');
    });

    test('throws ApiException on 413 — file too large', () async {
      stubSend(status: 413, body: 'File exceeds 25 MB limit');
      expect(
        () => client.uploadFile(Uint8List(0)),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 413)),
      );
    });

    test('throws ApiException on 415 — unsupported type', () async {
      stubSend(status: 415, body: 'Unsupported file type');
      expect(
        () => client.uploadFile(Uint8List(0)),
        throwsA(isA<ApiException>().having((e) => e.statusCode, 'statusCode', 415)),
      );
    });
  });

  // ── ApiException ──────────────────────────────────────────────────────────

  group('ApiException', () {
    test('toString includes status code and message', () {
      const e = ApiException(404, 'Not found');
      expect(e.toString(), 'ApiException(404): Not found');
    });

    test('is an Exception', () {
      expect(const ApiException(500, 'err'), isA<Exception>());
    });
  });
}
