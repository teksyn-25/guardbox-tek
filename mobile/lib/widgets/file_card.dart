import 'package:flutter/material.dart';

import '../models/file_item.dart';
import 'auth_image.dart';

class FileCard extends StatelessWidget {
  final FileItem file;
  final String baseUrl;
  final String token;
  final VoidCallback onTap;
  final VoidCallback onSave;
  final VoidCallback onDelete;

  const FileCard({
    super.key,
    required this.file,
    required this.baseUrl,
    required this.token,
    required this.onTap,
    required this.onSave,
    required this.onDelete,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Expanded(
              child: AuthImage(
                imageUrl: '$baseUrl/api/files/${file.fileId}/image',
                token: token,
                fit: BoxFit.cover,
              ),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              child: Row(
                children: [
                  _SourceChip(label: file.sourceLabel),
                  const Spacer(),
                  if (file.isPending)
                    IconButton(
                      icon: const Icon(Icons.bookmark_add_outlined, size: 20),
                      tooltip: 'Save',
                      onPressed: onSave,
                      visualDensity: VisualDensity.compact,
                    ),
                  IconButton(
                    icon: const Icon(Icons.delete_outline, size: 20),
                    tooltip: 'Delete',
                    onPressed: onDelete,
                    visualDensity: VisualDensity.compact,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _SourceChip extends StatelessWidget {
  final String label;

  const _SourceChip({required this.label});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(4),
      ),
      child: Text(
        label,
        style: Theme.of(context).textTheme.labelSmall,
      ),
    );
  }
}
