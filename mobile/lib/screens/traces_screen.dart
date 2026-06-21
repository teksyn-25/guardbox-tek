import 'package:flutter/material.dart';

import '../models/file_item.dart';
import '../theme.dart';

class TracesScreen extends StatelessWidget {
  final List<FileItem> files;
  final String baseUrl;
  final String token;

  const TracesScreen({
    super.key,
    required this.files,
    required this.baseUrl,
    required this.token,
  });

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Traces'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: files.isEmpty
          ? const Center(
              child: Text(
                'No traces yet.\nProcess a file to see what was stripped.',
                textAlign: TextAlign.center,
                style: TextStyle(color: kTextSecondary),
              ),
            )
          : ListView.separated(
              padding: const EdgeInsets.all(16),
              itemCount: files.length,
              separatorBuilder: (_, __) => const SizedBox(height: 8),
              itemBuilder: (ctx, i) => _TraceCard(file: files[i]),
            ),
    );
  }
}

class _TraceCard extends StatelessWidget {
  final FileItem file;

  const _TraceCard({required this.file});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: kCard,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: kCardBorder),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: kAccentDim,
                  borderRadius: BorderRadius.circular(4),
                ),
                child: Text(
                  file.sourceLabel,
                  style:
                      const TextStyle(color: kAccent, fontSize: 11),
                ),
              ),
              const SizedBox(width: 8),
              Text(
                '${file.sourceFormat.toUpperCase()} → ${file.outputFormat.toUpperCase()}',
                style:
                    const TextStyle(color: kTextSecondary, fontSize: 11),
              ),
              const Spacer(),
              Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: file.isPending ? kCard : kAccentDim,
                  borderRadius: BorderRadius.circular(4),
                  border: Border.all(
                    color: file.isPending ? kCardBorder : kAccent,
                  ),
                ),
                child: Text(
                  file.isPending ? 'Pending' : 'Safe',
                  style: TextStyle(
                    color: file.isPending ? kTextSecondary : kAccent,
                    fontSize: 10,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          const Text(
            'Stripped',
            style: TextStyle(color: kTextSecondary, fontSize: 11),
          ),
          const SizedBox(height: 6),
          file.stripped.isEmpty
              ? const Text(
                  'Nothing stripped',
                  style: TextStyle(color: kTextSecondary, fontSize: 12),
                )
              : Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: file.stripped
                      .map((s) => Container(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 8, vertical: 3),
                            decoration: BoxDecoration(
                              color: kDangerDim,
                              borderRadius: BorderRadius.circular(4),
                              border: Border.all(
                                  color: kDanger.withOpacity(0.3)),
                            ),
                            child: Text(
                              s,
                              style: const TextStyle(
                                  color: kDanger, fontSize: 11),
                            ),
                          ))
                      .toList(),
                ),
        ],
      ),
    );
  }
}
