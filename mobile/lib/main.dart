import 'package:flutter/material.dart';

import 'config.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
import 'screens/password_setup_screen.dart';
import 'screens/setup_screen.dart';
import 'services/api_client.dart';
import 'services/share_handler.dart';
import 'theme.dart';

final navigatorKey = GlobalKey<NavigatorState>();

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const GuardBoxApp());
}

class GuardBoxApp extends StatefulWidget {
  const GuardBoxApp({super.key});

  @override
  State<GuardBoxApp> createState() => _GuardBoxAppState();
}

class _GuardBoxAppState extends State<GuardBoxApp> {
  @override
  void initState() {
    super.initState();
    _initShareHandler();
  }

  void _initShareHandler() async {
    final url = await getServerUrl();
    final token = await getToken();
    if (url == null || token == null) return;
    final api = ApiClient(baseUrl: url, token: token);
    ShareHandlerService.init(navigatorKey, api.uploadFile);
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'GuardBox',
      navigatorKey: navigatorKey,
      debugShowCheckedModeBanner: false,
      theme: guardBoxTheme(),
      home: const _StartupRouter(),
      routes: {
        '/setup':          (_) => const SetupScreen(),
        '/password-setup': (_) => const PasswordSetupScreen(),
        '/login':          (_) => const LoginScreen(),
        '/dashboard':      (_) => const DashboardScreen(),
      },
    );
  }
}

class _StartupRouter extends StatelessWidget {
  const _StartupRouter();

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<Widget>(
      future: _resolve(),
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Scaffold(
            body: Center(child: CircularProgressIndicator(color: kAccent)),
          );
        }
        return snapshot.data!;
      },
    );
  }

  Future<Widget> _resolve() async {
    final url = await getServerUrl();
    if (url == null || url.isEmpty) return const SetupScreen();
    final token = await getToken();
    if (token == null || token.isEmpty) return const LoginScreen();
    return const DashboardScreen();
  }
}
