class FileItem {
  final String fileId;
  final String source;
  final String sourceFormat;
  final List<String> stripped;
  final String outputFormat;
  final int width;
  final int height;
  final String state;

  const FileItem({
    required this.fileId,
    required this.source,
    required this.sourceFormat,
    required this.stripped,
    required this.outputFormat,
    required this.width,
    required this.height,
    required this.state,
  });

  factory FileItem.fromJson(Map<String, dynamic> json, {String state = 'pending'}) {
    final dims = json['dimensions'] as Map<String, dynamic>? ?? {};
    return FileItem(
      fileId: json['file_id'] as String,
      source: json['source'] as String,
      sourceFormat: json['source_format'] as String,
      stripped: List<String>.from(json['stripped'] as List),
      outputFormat: json['output_format'] as String,
      width: dims['width'] as int? ?? 0,
      height: dims['height'] as int? ?? 0,
      state: state,
    );
  }

  String get sourceLabel => source == 'telegram_bot' ? 'Telegram' : 'WhatsApp';
  bool get isPending => state == 'pending';
}
