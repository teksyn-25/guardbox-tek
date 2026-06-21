import 'package:flutter/material.dart';

/// Displays an image from the GuardBox backend using a Bearer token.
/// NetworkImage supports custom headers so no extra HTTP call needed.
class AuthImage extends StatelessWidget {
  final String imageUrl;
  final String token;
  final double? width;
  final double? height;
  final BoxFit fit;

  const AuthImage({
    super.key,
    required this.imageUrl,
    required this.token,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
  });

  @override
  Widget build(BuildContext context) {
    return Image(
      image: NetworkImage(imageUrl, headers: {'Authorization': 'Bearer $token'}),
      width: width,
      height: height,
      fit: fit,
      loadingBuilder: (ctx, child, progress) {
        if (progress == null) return child;
        return SizedBox(
          width: width,
          height: height,
          child: const Center(child: CircularProgressIndicator()),
        );
      },
      errorBuilder: (ctx, _, __) => SizedBox(
        width: width,
        height: height,
        child: const Icon(Icons.broken_image, size: 40),
      ),
    );
  }
}
