import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:sews_mobile/features/risk/presentation/risk_explanation_screen.dart';
import 'package:sews_mobile/features/risk/presentation/risk_widgets.dart';

import '../helpers/fixtures.dart';

RiskOverview _overview({
  String level = 'high',
  String provenance = 'synthetic',
  int history = 1,
  List<Map<String, dynamic>> factors = const [],
}) =>
    RiskOverview(
      history: [
        for (var i = 0; i < history; i++)
          RiskPrediction.fromJson(predictionRow(
            id: 'p$i',
            level: i == 0 ? level : 'watch',
            provenance: provenance,
            date: '2026-09-${(20 - i * 7).toString().padLeft(2, '0')}',
          )),
      ],
      latestFactors: factors.map(RiskFactor.fromJson).toList(),
    );

Widget _wrap(Widget child) => MaterialApp(home: Scaffold(body: SingleChildScrollView(child: child)));

void main() {
  for (final level in RiskLevel.values) {
    testWidgets('risk card shows the ${level.label} state from the data', (tester) async {
      await tester.pumpWidget(_wrap(RiskSummaryContent(overview: _overview(level: level.name), onExplain: () {})));
      expect(find.text(level.label), findsOneWidget);
      expect(find.bySemanticsLabel('Risk level: ${level.label}'), findsOneWidget);
      expect(find.text(riskCaveat), findsOneWidget);
    });
  }

  testWidgets('the raw probability is never displayed', (tester) async {
    await tester.pumpWidget(_wrap(RiskSummaryContent(overview: _overview(), onExplain: () {})));
    expect(find.textContaining('0.74'), findsNothing);
    expect(find.textContaining('74%'), findsNothing);
  });

  testWidgets('non-institutional models are labelled as demonstration signals', (tester) async {
    await tester.pumpWidget(_wrap(RiskSummaryContent(overview: _overview(provenance: 'synthetic'), onExplain: () {})));
    expect(find.textContaining('Demonstration signal'), findsOneWidget);
    await tester.pumpWidget(
        _wrap(RiskSummaryContent(overview: _overview(provenance: 'institutional'), onExplain: () {})));
    expect(find.textContaining('Demonstration signal'), findsNothing);
  });

  testWidgets('trend needs at least two predictions', (tester) async {
    await tester.pumpWidget(_wrap(RiskSummaryContent(overview: _overview(), onExplain: () {})));
    expect(find.text('A trend will appear after more updates.'), findsOneWidget);
    await tester.pumpWidget(_wrap(RiskSummaryContent(overview: _overview(history: 2), onExplain: () {})));
    expect(find.text('A trend will appear after more updates.'), findsNothing);
    expect(find.bySemanticsLabel(RegExp('Risk level:')), findsNWidgets(3)); // header + 2 trend badges
  });

  testWidgets('explanation lists exactly the stored factors', (tester) async {
    await tester.pumpWidget(MaterialApp(
      home: Scaffold(
        body: RiskExplanationContent(
          overview: _overview(factors: [
            factorRow(1, 'attendance_rate_last_14d', 0.52, 0.61),
            factorRow(2, 'mean_score_to_date', 81.5, -0.2),
            factorRow(3, 'mystery_feature', 7, 0.05),
          ]),
        ),
      ),
    ));
    expect(find.text('Attendance in the last 14 days'), findsOneWidget);
    expect(find.text('Value: 52% · Raised the risk estimate'), findsOneWidget);
    expect(find.text('Average score so far'), findsOneWidget);
    expect(find.text('Value: 81.5 · Lowered the risk estimate'), findsOneWidget);
    expect(find.text('mystery_feature'), findsOneWidget, reason: 'unknown keys are shown, not guessed');
    expect(find.byType(ListTile), findsNWidgets(3));
  });

  testWidgets('no stored factors: says so instead of inventing an explanation', (tester) async {
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: RiskExplanationContent(overview: _overview()))));
    expect(find.text('No explanation factors were stored for this signal.'), findsOneWidget);
  });

  testWidgets('risk prediction unavailable shows the empty state', (tester) async {
    await tester.pumpWidget(ProviderScope(
      overrides: [riskOverviewProvider.overrideWith((ref) async => const RiskOverview(history: [], latestFactors: []))],
      child: _wrap(RiskSummaryCard(onExplain: () {})),
    ));
    await tester.pumpAndSettle();
    expect(find.text('No early-warning signal is available yet.'), findsOneWidget);
  });
}
