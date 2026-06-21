import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:guardbox/theme.dart';
import 'package:guardbox/widgets/stat_card.dart';

Widget _card({
  required int count,
  required String label,
  required Color color,
  required IconData icon,
}) =>
    MaterialApp(
      theme: guardBoxTheme(),
      home: Scaffold(
        body: Center(
          child: SizedBox(
            width: 140,
            child: StatCard(
                count: count, label: label, color: color, icon: icon),
          ),
        ),
      ),
    );

void main() {
  group('StatCard', () {
    testWidgets('renders the count', (tester) async {
      await tester.pumpWidget(
          _card(count: 3, label: 'Safe', color: kAccent, icon: Icons.check_circle_outline));
      expect(find.text('3'), findsOneWidget);
    });

    testWidgets('renders zero count', (tester) async {
      await tester.pumpWidget(
          _card(count: 0, label: 'Threats', color: kDanger, icon: Icons.gpp_bad_outlined));
      expect(find.text('0'), findsOneWidget);
    });

    testWidgets('renders the label', (tester) async {
      await tester.pumpWidget(
          _card(count: 0, label: 'Scanning', color: kTextSecondary, icon: Icons.radar));
      expect(find.text('Scanning'), findsOneWidget);
    });

    testWidgets('Safe card uses accent green color', (tester) async {
      await tester.pumpWidget(
          _card(count: 5, label: 'Safe', color: kAccent, icon: Icons.check_circle_outline));
      // Text widget exists with the right count
      final textWidget = tester.widget<Text>(find.text('5'));
      expect(textWidget.style?.color, kAccent);
    });

    testWidgets('Threats card uses danger red color', (tester) async {
      await tester.pumpWidget(
          _card(count: 0, label: 'Threats', color: kDanger, icon: Icons.gpp_bad_outlined));
      final textWidget = tester.widget<Text>(find.text('0'));
      expect(textWidget.style?.color, kDanger);
    });

    testWidgets('renders icon', (tester) async {
      await tester.pumpWidget(
          _card(count: 2, label: 'Safe', color: kAccent, icon: Icons.check_circle_outline));
      expect(find.byIcon(Icons.check_circle_outline), findsOneWidget);
    });
  });
}
