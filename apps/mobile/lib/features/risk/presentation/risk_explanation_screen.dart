import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/risk/domain/feature_labels.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';
import 'package:sews_mobile/features/risk/presentation/risk_widgets.dart';

class RiskExplanationScreen extends ConsumerWidget {
  const RiskExplanationScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) => Scaffold(
        appBar: AppBar(title: const Text('About your signal')),
        body: AsyncValueView<RiskOverview>(
          value: ref.watch(riskOverviewProvider),
          onRetry: () => ref.invalidate(riskOverviewProvider),
          isEmpty: (o) => !o.hasPrediction,
          emptyMessage: 'No early-warning signal is available yet.',
          emptyIcon: Icons.hourglass_empty,
          data: (o) => RiskExplanationContent(overview: o),
        ),
      );
}

/// Shows ONLY the factors stored with the prediction. Labels name the factor; value and
/// direction come from the data. Nothing is inferred or invented in the app.
class RiskExplanationContent extends StatelessWidget {
  const RiskExplanationContent({super.key, required this.overview});

  final RiskOverview overview;

  @override
  Widget build(BuildContext context) {
    final latest = overview.latest!;
    final theme = Theme.of(context);
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Row(
          children: [
            RiskLevelBadge(level: latest.level, large: true),
            const SizedBox(width: 12),
            Expanded(child: Text('Updated ${formatDate(latest.predictionDate)}')),
          ],
        ),
        const SizedBox(height: 12),
        Text(riskCaveat, style: theme.textTheme.bodyMedium),
        if (latest.provenance != DataProvenance.institutional) ...[
          const SizedBox(height: 12),
          ProvenanceNotice(provenance: latest.provenance),
        ],
        const SizedBox(height: 24),
        Text('What the estimate was based on', style: theme.textTheme.titleMedium),
        const SizedBox(height: 8),
        if (overview.latestFactors.isEmpty)
          const Text('No explanation factors were stored for this signal.')
        else
          for (final factor in overview.latestFactors) _FactorTile(factor: factor),
        const SizedBox(height: 16),
        Text(
          'These factors show which information most influenced the model\'s estimate, in order of '
          'influence. They describe patterns in past data, not causes, and they are not a judgement about you.',
          style: theme.textTheme.bodySmall,
        ),
        const SizedBox(height: 8),
        Text('Model version: ${latest.modelVersion}', style: theme.textTheme.bodySmall),
      ],
    );
  }
}

class _FactorTile extends StatelessWidget {
  const _FactorTile({required this.factor});

  final RiskFactor factor;

  @override
  Widget build(BuildContext context) {
    final raises = factor.direction == FactorDirection.increasesRisk;
    final color = raises ? const Color(0xFFD84315) : const Color(0xFF2E7D32);
    return ListTile(
      contentPadding: EdgeInsets.zero,
      leading: CircleAvatar(
        backgroundColor: color.withValues(alpha: 0.12),
        child: Icon(raises ? Icons.arrow_upward : Icons.arrow_downward, color: color),
      ),
      title: Text(labelFor(factor.feature).label),
      subtitle: Text('Value: ${formatFactorValue(factor)} · ${directionText(factor.direction)}'),
    );
  }
}
