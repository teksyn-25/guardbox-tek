import 'package:flutter/material.dart';

import '../models/file_item.dart';
import '../theme.dart';
import '../widgets/auth_image.dart';

class ViewerScreen extends StatelessWidget {
  final FileItem file;
  final String baseUrl;
  final String token;
  final VoidCallback? onSave;
  final VoidCallback onDelete;

  const ViewerScreen({
    super.key,
    required this.file,
    required this.baseUrl,
    required this.token,
    required this.onSave,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    final imageUrl = '$baseUrl/api/files/${file.fileId}/image';

    return Scaffold(
      appBar: AppBar(
        title: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            const Icon(Icons.shield_outlined, color: kAccent, size: 16),
            const SizedBox(width: 6),
            Text(file.sourceLabel),
          ],
        ),
        actions: [
          if (file.isPending && onSave != null)
            IconButton(
              icon: const Icon(Icons.bookmark_add_outlined),
              tooltip: 'Save',
              onPressed: () {
                onSave!();
                Navigator.pop(context);
              },
            ),
          IconButton(
            icon: const Icon(Icons.delete_outline, color: kDanger),
            tooltip: 'Delete',
            onPressed: () {
              onDelete();
              Navigator.pop(context);
            },
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.fromLTRB(16, 8, 16, 32),
        children: [
          // Clean image
          ClipRRect(
            borderRadius: BorderRadius.circular(14),
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(color: kCardBorder),
                borderRadius: BorderRadius.circular(14),
              ),
              child: AuthImage(
                imageUrl: imageUrl,
                token: token,
                width: double.infinity,
                fit: BoxFit.contain,
              ),
            ),
          ),

          const SizedBox(height: 16),

          // Safe banner
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
            decoration: BoxDecoration(
              color: kAccentDim,
              borderRadius: BorderRadius.circular(10),
              border: Border.all(color: kAccent.withOpacity(0.3)),
            ),
            child: const Row(
              children: [
                Icon(Icons.verified_outlined, color: kAccent, size: 16),
                SizedBox(width: 8),
                Text(
                  'Reconstructed clean copy — original discarded',
                  style: TextStyle(color: kAccent, fontSize: 12),
                ),
              ],
            ),
          ),

          const SizedBox(height: 16),

          // CDR report card
          _CdrReport(file: file),
        ],
      ),
    );
  }
}

class _CdrReport extends StatelessWidget {
  final FileItem file;

  const _CdrReport({required this.file});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: kCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kCardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'CDR Report',
            style: TextStyle(
              color: kTextPrimary,
              fontWeight: FontWeight.w600,
              fontSize: 14,
            ),
          ),
          const Divider(height: 20),
          _Row(label: 'Source', value: file.sourceLabel),
          _Row(
            label: 'Input format',
            value: file.sourceFormat.toUpperCase(),
          ),
          _Row(
            label: 'Output format',
            value: file.outputFormat.toUpperCase(),
          ),
          _Row(
            label: 'Dimensions',
            value: '${file.width} × ${file.height} px',
          ),
          const SizedBox(height: 12),
          const Text(
            'METADATA STRIPPED',
            style: TextStyle(
              color: kTextSecondary,
              fontSize: 10,
              letterSpacing: 1,
            ),
          ),
          const SizedBox(height: 8),
          file.stripped.isEmpty
              ? const Text(
                  'Nothing stripped',
                  style: TextStyle(color: kTextSecondary, fontSize: 12),
                )
              : Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: file.stripped
                      .map(
                        (s) => Container(
                          padding: const EdgeInsets.symmetric(
                              horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: kDangerDim,
                            borderRadius: BorderRadius.circular(4),
                            border:
                                Border.all(color: kDanger.withOpacity(0.3)),
                          ),
                          child: Text(
                            s,
                            style:
                                const TextStyle(color: kDanger, fontSize: 11),
                          ),
                        ),
                      )
                      .toList(),
                ),
        ],
      ),
    );
  }
}

class _Row extends StatelessWidget {
  final String label;
  final String value;

  const _Row({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          SizedBox(
            width: 110,
            child: Text(
              label,
              style: const TextStyle(color: kTextSecondary, fontSize: 12),
            ),
          ),
          Expanded(
            child: Text(
              value,
              style: const TextStyle(color: kTextPrimary, fontSize: 12),
            ),
          ),
        ],
      ),
    );
  }
}
