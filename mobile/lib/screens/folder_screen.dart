import 'package:flutter/material.dart';

import '../models/file_item.dart';
import '../services/api_client.dart';
import '../theme.dart';
import '../widgets/file_card.dart';
import 'viewer_screen.dart';

class FolderScreen extends StatefulWidget {
  final String label;
  final IconData icon;
  final List<FileItem> files;
  final String baseUrl;
  final String token;
  final ApiClient api;
  final VoidCallback onChanged;

  const FolderScreen({
    super.key,
    required this.label,
    required this.icon,
    required this.files,
    required this.baseUrl,
    required this.token,
    required this.api,
    required this.onChanged,
  });

  @override
  State<FolderScreen> createState() => _FolderScreenState();
}

class _FolderScreenState extends State<FolderScreen> {
  late List<FileItem> _files;

  @override
  void initState() {
    super.initState();
    _files = List.from(widget.files);
  }

  Future<void> _save(FileItem file) async {
    try {
      await widget.api.saveFile(file.fileId);
      setState(() {
        final i = _files.indexWhere((f) => f.fileId == file.fileId);
        if (i != -1) {
          _files[i] = FileItem(
            fileId: file.fileId,
            source: file.source,
            sourceFormat: file.sourceFormat,
            stripped: file.stripped,
            outputFormat: file.outputFormat,
            width: file.width,
            height: file.height,
            state: 'saved',
          );
        }
      });
      widget.onChanged();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  Future<void> _delete(FileItem file) async {
    try {
      await widget.api.deleteFile(file.fileId);
      setState(() => _files.removeWhere((f) => f.fileId == file.fileId));
      widget.onChanged();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  void _openViewer(FileItem file) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ViewerScreen(
          file: file,
          baseUrl: widget.baseUrl,
          token: widget.token,
          onSave: file.isPending ? () => _save(file) : null,
          onDelete: () => _delete(file),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(widget.icon, color: kAccent, size: 18),
            const SizedBox(width: 8),
            Text(widget.label),
          ],
        ),
      ),
      body: _files.isEmpty
          ? const Center(
              child: Text(
                'No images yet.',
                style: TextStyle(color: kTextSecondary),
              ),
            )
          : GridView.builder(
              padding: const EdgeInsets.all(12),
              gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
                crossAxisCount: 2,
                mainAxisSpacing: 8,
                crossAxisSpacing: 8,
                childAspectRatio: 0.85,
              ),
              itemCount: _files.length,
              itemBuilder: (ctx, i) {
                final file = _files[i];
                return FileCard(
                  file: file,
                  baseUrl: widget.baseUrl,
                  token: widget.token,
                  onTap: () => _openViewer(file),
                  onSave: () => _save(file),
                  onDelete: () => _delete(file),
                );
              },
            ),
    );
  }
}
