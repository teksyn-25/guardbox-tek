import 'package:flutter/material.dart';

import '../theme.dart';

class SourceFolderCard extends StatelessWidget {
  final String name;
  final int count;
  final IconData icon;
  final VoidCallback onTap;

  const SourceFolderCard({
    super.key,
    required this.name,
    required this.count,
    required this.icon,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: kCard,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: kCardBorder),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: kAccentDim,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Icon(icon, color: kAccent, size: 18),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    name,
                    style: const TextStyle(
                      color: kTextPrimary,
                      fontWeight: FontWeight.w600,
                      fontSize: 13,
                    ),
                  ),
                  Text(
                    '$count ${count == 1 ? 'image' : 'images'}',
                    style: const TextStyle(
                      color: kTextSecondary,
                      fontSize: 11,
                    ),
                  ),
                ],
              ),
            ),
            Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: count > 0 ? kAccentDim : kCard,
                shape: BoxShape.circle,
                border: Border.all(
                  color: count > 0 ? kAccent : kCardBorder,
                  width: 1.5,
                ),
              ),
              child: count > 0
                  ? const Icon(Icons.check, color: kAccent, size: 13)
                  : null,
            ),
          ],
        ),
      ),
    );
  }
}
