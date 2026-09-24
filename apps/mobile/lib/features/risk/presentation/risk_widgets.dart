import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/core/widgets/section_card.dart';
import 'package:sews_mobile/core/widgets/state_views.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';

/// Caveat shown with every signal.
const String riskCaveat =
    'This is an estimate from a statistical model, not a prediction of your results. '
    'It is meant to help you and your mentor decide whether support could help.';

Color riskColor(RiskLevel level) => switch (level) {
      RiskLevel.stable => const Color(0xFF2E7D32),
      RiskLevel.watch => const Color(0xFF8D6E00),
      RiskLevel.elevated => const Color(0xFFD84315),
      RiskLevel.high => const Color(0xFFC62828),
    };

IconData riskIcon(RiskLevel level) => switch (level) {
      RiskLevel.stable => Icons.check_circle_outline,
      RiskLevel.watch => Icons.visibility_outlined,
      RiskLevel.elevated => Icons.trending_up,
      RiskLevel.high => Icons.priority_high,
    };

/// Level shown with colour, icon AND text so it never relies on colour alone.
class RiskLevelBadge extends StatelessWidget {
  const RiskLevelBadge({super.key, required this.level, this.large = false});

  final RiskLevel level;
  final bool large;

  @override
  Widget build(BuildContext context) {
    final color = riskColor(level);
    return Semantics(
      label: 'Risk level: ${level.label}',
      excludeSemantics: true,
      child: Container(
        padding: EdgeInsets.symmetric(horizontal: large ? 16 : 10, vertical: large ? 8 : 4),
        decoration: BoxDecoration(
          color: color.withValues(alpha: 0.12),
          border: Border.all(color: color),
          borderRadius: BorderRadius.circular(24),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(riskIcon(level), color: color, size: large ? 24 : 16),
            const SizedBox(width: 6),
            Text(
              level.label,
              style: (large ? Theme.of(context).textTheme.titleLarge : Theme.of(context).textTheme.labelLarge)
                  ?.copyWith(color: color, fontWeight: FontWeight.w600),
            ),
          ],
        ),
      ),
    );
  }
}

/// Explains when a signal does not come from a model validated on institutional data.
class ProvenanceNotice extends StatelessWidget {
  const ProvenanceNotice({super.key, required this.provenance});

  final DataProvenance provenance;

  static String? messageFor(DataProvenance provenance) => switch (provenance) {
        DataProvenance.institutional => null,
        DataProvenance.benchmark =>
          'Demonstration signal: produced by a model trained on public benchmark data that has not '
              'been validated for your institution.',
        DataProvenance.synthetic =>
          'Demonstration signal: produced from synthetic test data. It does not describe your situation.',
      };

  @override
  Widget build(BuildContext context) {
    final message = messageFor(provenance);
    if (message == null) return const SizedBox.shrink();
    final scheme = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(color: scheme.tertiaryContainer, borderRadius: BorderRadius.circular(8)),
      child: Row(
        children: [
          Icon(Icons.science_outlined, color: scheme.onTertiaryContainer, size: 18),
          const SizedBox(width: 8),
          Expanded(child: Text(message, style: TextStyle(color: scheme.onTertiaryContainer))),
        ],
      ),
    );
  }
}

class RiskTrendRow extends StatelessWidget {
  const RiskTrendRow({super.key, required this.overview});

  final RiskOverview overview;

  @override
  Widget build(BuildContext context) {
    final trend = overview.trend;
    if (trend.length < 2) {
      return Text('A trend will appear after more updates.', style: Theme.of(context).textTheme.bodySmall);
    }
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      crossAxisAlignment: WrapCrossAlignment.center,
      children: [
        for (var i = 0; i < trend.length; i++) ...[
          if (i > 0) const Icon(Icons.chevron_right, size: 16),
          Tooltip(
            message: formatDate(trend[i].predictionDate),
            child: RiskLevelBadge(level: trend[i].level),
          ),
        ],
      ],
    );
  }
}

/// The body of the dashboard risk card for a loaded overview that has a prediction.
class RiskSummaryContent extends StatelessWidget {
  const RiskSummaryContent({super.key, required this.overview, required this.onExplain});

  final RiskOverview overview;
  final VoidCallback onExplain;

  @override
  Widget build(BuildContext context) {
    final latest = overview.latest!;
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            RiskLevelBadge(level: latest.level, large: true),
            const SizedBox(width: 12),
            Expanded(child: Text('Updated ${formatDate(latest.predictionDate)}', style: theme.textTheme.bodySmall)),
          ],
        ),
        if (latest.trajectory != Trajectory.insufficientHistory) ...[
          const SizedBox(height: 8),
          Text('Direction since last update: ${latest.trajectory.studentLabel}', style: theme.textTheme.bodyMedium),
        ],
        const SizedBox(height: 12),
        Text(riskCaveat, style: theme.textTheme.bodyMedium),
        if (latest.provenance != DataProvenance.institutional) ...[
          const SizedBox(height: 12),
          ProvenanceNotice(provenance: latest.provenance),
        ],
        const SizedBox(height: 12),
        Text('Recent trend', style: theme.textTheme.labelLarge),
        const SizedBox(height: 6),
        RiskTrendRow(overview: overview),
        const SizedBox(height: 8),
        Align(
          alignment: Alignment.centerRight,
          child: TextButton.icon(
            onPressed: onExplain,
            icon: const Icon(Icons.insights_outlined),
            label: const Text('Why this signal?'),
          ),
        ),
      ],
    );
  }
}

class RiskSummaryCard extends ConsumerWidget {
  const RiskSummaryCard({super.key, required this.onExplain});

  final VoidCallback onExplain;

  @override
  Widget build(BuildContext context, WidgetRef ref) => SectionCard(
        title: 'Early-warning signal',
        child: AsyncValueView<RiskOverview>(
          value: ref.watch(riskOverviewProvider),
          onRetry: () => ref.invalidate(riskOverviewProvider),
          compact: true,
          isEmpty: (o) => !o.hasPrediction,
          emptyMessage: 'No early-warning signal is available yet.',
          emptyIcon: Icons.hourglass_empty,
          data: (o) => RiskSummaryContent(overview: o, onExplain: onExplain),
        ),
      );
}
