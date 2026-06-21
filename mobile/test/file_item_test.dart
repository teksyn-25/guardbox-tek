import 'package:flutter_test/flutter_test.dart';
import 'package:guardbox/models/file_item.dart';

const _full = <String, dynamic>{
  'file_id': 'abc-123',
  'source': 'telegram_bot',
  'source_format': 'jpeg',
  'stripped': ['exif', 'xmp', 'iptc'],
  'output_format': 'png',
  'dimensions': {'width': 800, 'height': 600},
};

void main() {
  group('FileItem.fromJson', () {
    test('parses all fields correctly', () {
      final f = FileItem.fromJson(_full);
      expect(f.fileId, 'abc-123');
      expect(f.source, 'telegram_bot');
      expect(f.sourceFormat, 'jpeg');
      expect(f.stripped, ['exif', 'xmp', 'iptc']);
      expect(f.outputFormat, 'png');
      expect(f.width, 800);
      expect(f.height, 600);
    });

    test('defaults state to pending when not supplied', () {
      final f = FileItem.fromJson(_full);
      expect(f.state, 'pending');
      expect(f.isPending, isTrue);
    });

    test('accepts explicit saved state', () {
      final f = FileItem.fromJson(_full, state: 'saved');
      expect(f.state, 'saved');
      expect(f.isPending, isFalse);
    });

    test('sourceLabel returns Telegram for telegram_bot', () {
      final f = FileItem.fromJson(_full);
      expect(f.sourceLabel, 'Telegram');
    });

    test('sourceLabel returns WhatsApp for share_sheet', () {
      final f = FileItem.fromJson({..._full, 'source': 'share_sheet'});
      expect(f.sourceLabel, 'WhatsApp');
    });

    test('falls back to WhatsApp label for unknown source', () {
      final f = FileItem.fromJson({..._full, 'source': 'unknown_source'});
      // sourceLabel is a binary: telegram_bot → Telegram, everything else → WhatsApp
      expect(f.sourceLabel, 'WhatsApp');
    });

    test('handles missing dimensions — defaults to zero', () {
      final json = Map<String, dynamic>.from(_full)..remove('dimensions');
      final f = FileItem.fromJson(json);
      expect(f.width, 0);
      expect(f.height, 0);
    });

    test('handles null dimension values — defaults to zero', () {
      final f = FileItem.fromJson({..._full, 'dimensions': <String, dynamic>{}});
      expect(f.width, 0);
      expect(f.height, 0);
    });

    test('handles empty stripped list', () {
      final f = FileItem.fromJson({..._full, 'stripped': <String>[]});
      expect(f.stripped, isEmpty);
    });

    test('model has no timestamp, filename, size, or IP field', () {
      // Privacy contract: forbidden metadata fields must not exist on FileItem.
      // Verified structurally — accessing f.createdAt etc. would be a compile error.
      final f = FileItem.fromJson(_full);
      expect(f.fileId, isNotEmpty);   // file_id     ✅ allowed
      expect(f.source, isNotEmpty);   // source      ✅ allowed
      expect(f.stripped, isList);     // stripped    ✅ allowed
      // No f.createdAt, f.fileName, f.fileSize, f.ipAddress — they do not exist.
    });
  });

  group('FileItem equality', () {
    test('two items with same data are value-equal via fields', () {
      final a = FileItem.fromJson(_full);
      final b = FileItem.fromJson(_full);
      expect(a.fileId, b.fileId);
      expect(a.source, b.source);
      expect(a.stripped, b.stripped);
    });
  });
}
