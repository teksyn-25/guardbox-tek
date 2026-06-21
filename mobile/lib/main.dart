import 'package:app_links/app_links.dart';
import 'package:flutter/material.dart';

import 'config.dart';
import 'screens/dashboard_screen.dart';
import 'screens/login_screen.dart';
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
  late final AppLinks _appLinks;

  @override
  void initState() {
    super.initState();
    _appLinks = AppLinks();
    _appLinks.uriLinkStream.listen(_onDeepLink);
    _initShareHandler();
  }

  void _initShareHandler() async {
    final url = await getServerUrl();
    final token = await getToken();
    if (url == null || token == null) return;
    final api = ApiClient(baseUrl: url, token: token);
    ShareHandlerService.init(navigatorKey, api.uploadFile);
  }

  void _onDeepLink(Uri uri) async {
    if (uri.scheme != 'guardbox' || uri.host != 'auth') return;
    final token = uri.queryParameters['token'];
    if (token == null) return;
    await setToken(token);
    navigatorKey.currentState
        ?.pushNamedAndRemoveUntil('/dashboard', (_) => false);
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
        '/setup': (_) => const SetupScreen(),
        '/login': (_) => const LoginScreen(),
        '/dashboard': (_) => const DashboardScreen(),
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
