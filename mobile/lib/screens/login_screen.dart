import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

import '../config.dart';
import '../theme.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key});

  Future<void> _login(BuildContext context) async {
    final serverUrl = await getServerUrl();
    if (serverUrl == null) {
      if (context.mounted) Navigator.pushReplacementNamed(context, '/setup');
      return;
    }
    final uri = Uri.parse('$serverUrl/auth/login?app=1');
    if (!await launchUrl(uri, mode: LaunchMode.externalApplication)) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Could not open browser')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(28),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Logo
              Center(
                child: Container(
                  padding: const EdgeInsets.all(16),
                  decoration: BoxDecoration(
                    color: kAccentDim,
                    borderRadius: BorderRadius.circular(16),
                    boxShadow: [
                      BoxShadow(
                        color: kAccent.withOpacity(0.35),
                        blurRadius: 32,
                        spreadRadius: 2,
                      ),
                    ],
                  ),
                  child: const Icon(Icons.view_in_ar, color: kAccent, size: 48),
                ),
              ),
              const SizedBox(height: 24),
              const Text(
                'GuardBox',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: kAccent,
                  fontSize: 30,
                  fontWeight: FontWeight.w300,
                  letterSpacing: 2,
                ),
              ),
              const SizedBox(height: 8),
              const Text(
                'Open files securely.',
                textAlign: TextAlign.center,
                style: TextStyle(color: kTextSecondary, fontSize: 14),
              ),
              const SizedBox(height: 48),
              FilledButton.icon(
                onPressed: () => _login(context),
                icon: const Icon(Icons.near_me_outlined, size: 18),
                label: const Text('Login with Telegram'),
              ),
              const SizedBox(height: 12),
              TextButton(
                onPressed: () =>
                    Navigator.pushReplacementNamed(context, '/setup'),
                child: const Text('Change server'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
