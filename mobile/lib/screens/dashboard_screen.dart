import 'package:file_picker/file_picker.dart';
import 'package:flutter/material.dart';

import '../config.dart';
import '../models/file_item.dart';
import '../services/api_client.dart';
import '../theme.dart';
import '../widgets/stat_card.dart';
import '../widgets/source_folder_card.dart';
import 'folder_screen.dart';
import 'traces_screen.dart';

class DashboardScreen extends StatefulWidget {
  /// Production constructor — resolves server URL and token from storage.
  const DashboardScreen({super.key}) : _testApi = null;

  /// Test-only constructor — injects a pre-built ApiClient, skips storage.
  @visibleForTesting
  const DashboardScreen.testable({required ApiClient api, super.key})
      : _testApi = api;

  final ApiClient? _testApi;

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  List<FileItem> _all = [];
  bool _loading = true;
  bool _uploading = false;
  String? _error;
  ApiClient? _api;
  String _baseUrl = '';
  String _token = '';

  // files grouped by source
  List<FileItem> _forSource(String source) =>
      _all.where((f) => f.source == source).toList();

  List<FileItem> get _other => _all
      .where((f) => f.source != 'telegram_bot' && f.source != 'share_sheet')
      .toList();

  int get _safeCount => _all.where((f) => !f.isPending).length;
  int get _scanningCount => _all.where((f) => f.isPending).length;

  @override
  void initState() {
    super.initState();
    _init();
  }

  Future<void> _init() async {
    if (widget._testApi != null) {
      setState(() { _api = widget._testApi; });
      await _load();
      return;
    }
    final url = await getServerUrl();
    final tok = await getToken();
    if (url == null || tok == null) {
      if (mounted) Navigator.pushReplacementNamed(context, '/login');
      return;
    }
    setState(() {
      _baseUrl = url;
      _token = tok;
      _api = ApiClient(baseUrl: url, token: tok);
    });
    await _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final results = await Future.wait([
        _api!.listFiles('pending'),
        _api!.listFiles('saved'),
      ]);
      if (mounted) {
        setState(() {
          _all = [...results[0], ...results[1]];
          _loading = false;
        });
      }
    } on ApiException catch (e) {
      if (e.statusCode == 401) {
        await clearToken();
        if (mounted) Navigator.pushReplacementNamed(context, '/login');
      } else {
        if (mounted) setState(() { _loading = false; _error = e.toString(); });
      }
    }
  }

  Future<void> _clearAll() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: kCard,
        title: const Text('Clear all files?'),
        content: const Text(
          'This will permanently delete all your images.',
          style: TextStyle(color: kTextSecondary),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Clear all', style: TextStyle(color: kDanger)),
          ),
        ],
      ),
    );
    if (confirmed != true) return;
    try {
      await Future.wait(_all.map((f) => _api!.deleteFile(f.fileId)));
      await _load();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    }
  }

  void _openFolder(String source, String label, IconData icon) {
    Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => FolderScreen(
          label: label,
          icon: icon,
          files: source == 'other'
              ? _other
              : _forSource(source),
          baseUrl: _baseUrl,
          token: _token,
          api: _api!,
          onChanged: _load,
        ),
      ),
    );
  }

  Future<void> _pickAndUpload() async {
    final result = await FilePicker.platform.pickFiles(
      type: FileType.image,
      withData: true,   // bytes in-memory — no path stored or transmitted
    );
    if (result == null || result.files.single.bytes == null) return;
    final bytes = result.files.single.bytes!;
    setState(() => _uploading = true);
    try {
      await _api!.uploadFile(bytes);
      await _load();
    } on ApiException catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(e.message)));
      }
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  void dispose() {
    _api?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        toolbarHeight: 64,
        leading: Padding(
          padding: const EdgeInsets.only(left: 12),
          child: GestureDetector(
            onTap: () async {
              await clearToken();
              if (mounted) Navigator.pushReplacementNamed(context, '/login');
            },
            child: const Column(
              mainAxisAlignment: MainAxisAlignment.center,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Icon(Icons.shield_outlined, color: kAccent, size: 18),
                SizedBox(height: 2),
                Text(
                  '>) Login',
                  style: TextStyle(color: kAccent, fontSize: 10),
                ),
              ],
            ),
          ),
        ),
        title: Column(
          children: [
            Container(
              padding: const EdgeInsets.all(6),
              decoration: BoxDecoration(
                color: kAccentDim,
                borderRadius: BorderRadius.circular(8),
                boxShadow: [
                  BoxShadow(
                    color: kAccent.withOpacity(0.35),
                    blurRadius: 16,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: const Icon(Icons.view_in_ar, color: kAccent, size: 22),
            ),
          ],
        ),
        centerTitle: true,
        actions: [
          Padding(
            padding: const EdgeInsets.only(right: 12),
            child: TextButton(
              onPressed: () => Navigator.push(
                context,
                MaterialPageRoute(
                  builder: (_) => TracesScreen(
                    files: _all,
                    baseUrl: _baseUrl,
                    token: _token,
                  ),
                ),
              ),
              style: TextButton.styleFrom(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                side: const BorderSide(color: kCardBorder),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
              ),
              child: const Text(
                '> Traces',
                style: TextStyle(color: kTextSecondary, fontSize: 12),
              ),
            ),
          ),
        ],
      ),
      body: _loading
          ? const Center(child: CircularProgressIndicator(color: kAccent))
          : _error != null
              ? _ErrorView(error: _error!, onRetry: _load)
              : RefreshIndicator(
                  color: kAccent,
                  backgroundColor: kCard,
                  onRefresh: _load,
                  child: ListView(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 100),
                    children: [
                      // GuardBox title
                      const Padding(
                        padding: EdgeInsets.symmetric(vertical: 12),
                        child: Text(
                          'GuardBox',
                          textAlign: TextAlign.center,
                          style: TextStyle(
                            color: kAccent,
                            fontSize: 26,
                            fontWeight: FontWeight.w300,
                            letterSpacing: 2,
                          ),
                        ),
                      ),

                      // Stats row
                      Row(
                        children: [
                          Expanded(
                            child: StatCard(
                              count: _safeCount,
                              label: 'Safe',
                              color: kAccent,
                              icon: Icons.check_circle_outline,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: StatCard(
                              count: _scanningCount,
                              label: 'Scanning',
                              color: kTextSecondary,
                              icon: Icons.radar,
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: StatCard(
                              count: 0,
                              label: 'Threats',
                              color: kDanger,
                              icon: Icons.gpp_bad_outlined,
                            ),
                          ),
                        ],
                      ),

                      const SizedBox(height: 24),

                      // Section header
                      Row(
                        children: [
                          const Text(
                            'Your Images',
                            style: TextStyle(
                              color: kTextPrimary,
                              fontSize: 15,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                          const Spacer(),
                          if (_all.isNotEmpty)
                            GestureDetector(
                              onTap: _clearAll,
                              child: const Row(
                                children: [
                                  Icon(Icons.delete_sweep_outlined,
                                      size: 14, color: kTextSecondary),
                                  SizedBox(width: 4),
                                  Text(
                                    'Clear all',
                                    style: TextStyle(
                                      color: kTextSecondary,
                                      fontSize: 12,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                        ],
                      ),

                      const SizedBox(height: 12),

                      // Source folder cards — 3 columns
                      Row(
                        children: [
                          Expanded(
                            child: SourceFolderCard(
                              name: 'WhatsApp',
                              count: _forSource('share_sheet').length,
                              icon: Icons.chat_bubble_outline,
                              onTap: () => _openFolder(
                                'share_sheet',
                                'WhatsApp',
                                Icons.chat_bubble_outline,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: SourceFolderCard(
                              name: 'Telegram',
                              count: _forSource('telegram_bot').length,
                              icon: Icons.near_me_outlined,
                              onTap: () => _openFolder(
                                'telegram_bot',
                                'Telegram',
                                Icons.near_me_outlined,
                              ),
                            ),
                          ),
                          const SizedBox(width: 8),
                          Expanded(
                            child: SourceFolderCard(
                              name: 'Other',
                              count: _other.length,
                              icon: Icons.perm_media_outlined,
                              onTap: () => _openFolder(
                                'other',
                                'Other',
                                Icons.perm_media_outlined,
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
      floatingActionButton: FloatingActionButton(
        onPressed: _uploading ? null : _pickAndUpload,
        backgroundColor: _uploading ? kCard : kAccent,
        child: _uploading
            ? const SizedBox(
                width: 22,
                height: 22,
                child: CircularProgressIndicator(
                  strokeWidth: 2.5,
                  color: kAccent,
                ),
              )
            : const Icon(Icons.add, color: Color(0xFF04231a)),
      ),
    );
  }
}

class _ErrorView extends StatelessWidget {
  final String error;
  final VoidCallback onRetry;

  const _ErrorView({required this.error, required this.onRetry});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(error, style: const TextStyle(color: kDanger)),
          const SizedBox(height: 16),
          FilledButton(onPressed: onRetry, child: const Text('Retry')),
        ],
      ),
    );
  }
}
