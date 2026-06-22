import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;

import '../config.dart';
import '../theme.dart';

class SetupScreen extends StatefulWidget {
  const SetupScreen({super.key});

  @override
  State<SetupScreen> createState() => _SetupScreenState();
}

class _SetupScreenState extends State<SetupScreen> {
  final _controller = TextEditingController();
  final _formKey = GlobalKey<FormState>();
  bool _saving = false;
  String? _error;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() { _saving = true; _error = null; });

    final url = _controller.text.trim().replaceAll(RegExp(r'/+$'), '');

    try {
      final res = await http.get(Uri.parse('$url/api/auth/status'));
      if (res.statusCode != 200) {
        setState(() { _error = 'Could not connect to server.'; });
        return;
      }
      await setServerUrl(url);
      final setupDone = (jsonDecode(res.body) as Map<String, dynamic>)['setup_done'] as bool;
      if (mounted) {
        Navigator.pushReplacementNamed(
          context,
          setupDone ? '/login' : '/password-setup',
        );
      }
    } catch (_) {
      setState(() { _error = 'Could not connect to server.'; });
    } finally {
      if (mounted) setState(() => _saving = false);
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
                'Enter your server address to get started.',
                textAlign: TextAlign.center,
                style: TextStyle(color: kTextSecondary, fontSize: 13),
              ),
              const SizedBox(height: 40),
              Form(
                key: _formKey,
                child: TextFormField(
                  controller: _controller,
                  keyboardType: TextInputType.url,
                  autocorrect: false,
                  style: const TextStyle(color: kTextPrimary),
                  decoration: const InputDecoration(
                    labelText: 'Server URL',
                    hintText: 'https://guardbox.example.com',
                    prefixIcon: Icon(Icons.dns_outlined, color: kAccent, size: 18),
                  ),
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Required';
                    final uri = Uri.tryParse(v.trim());
                    if (uri == null || !uri.hasScheme) return 'Enter a valid URL';
                    if (uri.scheme != 'https') return 'HTTPS required — plaintext HTTP is not allowed';
                    return null;
                  },
                ),
              ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(_error!, style: const TextStyle(color: Colors.redAccent, fontSize: 13)),
              ],
              const SizedBox(height: 24),
              FilledButton(
                onPressed: _saving ? null : _save,
                child: _saving
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2, color: Colors.black),
                      )
                    : const Text('Continue'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
