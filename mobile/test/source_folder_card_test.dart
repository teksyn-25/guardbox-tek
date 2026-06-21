import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:guardbox/theme.dart';
import 'package:guardbox/widgets/source_folder_card.dart';

Widget _card({
  required String name,
  required int count,
  required IconData icon,
  VoidCallback? onTap,
}) =>
    MaterialApp(
      theme: guardBoxTheme(),
      home: Scaffold(
        body: Padding(
          padding: const EdgeInsets.all(16),
          child: SourceFolderCard(
            name: name,
            count: count,
            icon: icon,
            onTap: onTap ?? () {},
          ),
        ),
      ),
    );

void main() {
  group('SourceFolderCard', () {
    testWidgets('renders folder name', (tester) async {
      await tester.pumpWidget(
          _card(name: 'Telegram', count: 3, icon: Icons.near_me_outlined));
      expect(find.text('Telegram'), findsOneWidget);
    });

    testWidgets('renders singular "image" for count 1', (tester) async {
      await tester.pumpWidget(
          _card(name: 'WhatsApp', count: 1, icon: Icons.chat_bubble_outline));
      expect(find.text('1 image'), findsOneWidget);
    });

    testWidgets('renders plural "images" for count 0', (tester) async {
      await tester.pumpWidget(
          _card(name: 'Other', count: 0, icon: Icons.perm_media_outlined));
      expect(find.text('0 images'), findsOneWidget);
    });

    testWidgets('renders plural "images" for count > 1', (tester) async {
      await tester.pumpWidget(
          _card(name: 'Telegram', count: 5, icon: Icons.near_me_outlined));
      expect(find.text('5 images'), findsOneWidget);
    });

    testWidgets('shows checkmark icon when count > 0', (tester) async {
      await tester.pumpWidget(
          _card(name: 'Telegram', count: 3, icon: Icons.near_me_outlined));
      expect(find.byIcon(Icons.check), findsOneWidget);
    });

    testWidgets('hides checkmark icon when count is 0', (tester) async {
      await tester.pumpWidget(
          _card(name: 'Other', count: 0, icon: Icons.perm_media_outlined));
      expect(find.byIcon(Icons.check), findsNothing);
    });

    testWidgets('calls onTap when tapped', (tester) async {
      var tapped = false;
      await tester.pumpWidget(
          _card(name: 'WhatsApp', count: 2, icon: Icons.chat_bubble_outline,
              onTap: () => tapped = true));
      await tester.tap(find.byType(SourceFolderCard));
      expect(tapped, isTrue);
    });

    testWidgets('renders the source icon', (tester) async {
      await tester.pumpWidget(
          _card(name: 'Telegram', count: 0, icon: Icons.near_me_outlined));
      expect(find.byIcon(Icons.near_me_outlined), findsOneWidget);
    });
  });
}
