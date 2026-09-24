import 'package:sews_mobile/core/formatting.dart';
import 'package:sews_mobile/features/risk/domain/risk_models.dart';

enum ValueFormat { fractionAsPercent, count, days, score, perDay, gpa, raw }

class FeatureLabel {
  const FeatureLabel(this.label, this.format);

  final String label;
  final ValueFormat format;
}

/// Display names for model feature keys (docs/ml/data-dictionary.md,
/// ml/features/definitions.py). Only the NAME and unit come from here. Whether a factor
/// raised or lowered the estimate, and its value, always come from the stored factor.
/// Unknown keys are shown as-is rather than guessed.
const Map<String, FeatureLabel> featureLabels = {
  // Institutional feature set (data dictionary)
  'attendance_rate_to_date': FeatureLabel('Attendance so far this term', ValueFormat.fractionAsPercent),
  'attendance_rate_last_14d': FeatureLabel('Attendance in the last 14 days', ValueFormat.fractionAsPercent),
  'attendance_trend': FeatureLabel('Change in weekly attendance', ValueFormat.raw),
  'consecutive_absences': FeatureLabel('Consecutive absences', ValueFormat.count),
  'missed_submission_rate': FeatureLabel('Assignments not submitted', ValueFormat.fractionAsPercent),
  'mean_released_score_pct': FeatureLabel('Average released score', ValueFormat.score),
  'weighted_score_to_date': FeatureLabel('Weighted score so far', ValueFormat.score),
  'engagement_active_days_14d': FeatureLabel('Active learning days in the last 14 days', ValueFormat.count),
  'engagement_trend': FeatureLabel('Change in learning activity', ValueFormat.raw),
  'prior_term_gpa': FeatureLabel('Previous semester GPA', ValueFormat.gpa),
  'prior_attempts': FeatureLabel('Previous attempts at this course', ValueFormat.count),
  // Benchmark (OULAD) feature set
  'clicks_to_date': FeatureLabel('Learning-platform activity so far', ValueFormat.count),
  'active_days_to_date': FeatureLabel('Days active on the learning platform', ValueFormat.count),
  'clicks_last_7d': FeatureLabel('Learning-platform activity, last 7 days', ValueFormat.count),
  'clicks_last_14d': FeatureLabel('Learning-platform activity, last 14 days', ValueFormat.count),
  'clicks_last_30d': FeatureLabel('Learning-platform activity, last 30 days', ValueFormat.count),
  'clicks_trend_7d': FeatureLabel('Change in daily activity (7-day windows)', ValueFormat.perDay),
  'clicks_trend_14d': FeatureLabel('Change in daily activity (14-day windows)', ValueFormat.perDay),
  'clicks_trend_30d': FeatureLabel('Change in daily activity (30-day windows)', ValueFormat.perDay),
  'clicks_change_from_baseline': FeatureLabel('Recent activity compared with your usual level', ValueFormat.perDay),
  'days_since_last_activity': FeatureLabel('Days since last learning-platform activity', ValueFormat.days),
  'assessments_due_to_date': FeatureLabel('Assessments due so far', ValueFormat.count),
  'assignment_completion_rate': FeatureLabel('Assessments submitted', ValueFormat.fractionAsPercent),
  'late_submission_rate': FeatureLabel('Submissions made after the due date', ValueFormat.fractionAsPercent),
  'mean_submission_delay_days': FeatureLabel('Average submission timing (days vs due date)', ValueFormat.days),
  'mean_score_to_date': FeatureLabel('Average score so far', ValueFormat.score),
  'last_score': FeatureLabel('Most recent score', ValueFormat.score),
  'course_relative_score': FeatureLabel('Average score compared with your cohort', ValueFormat.score),
  'num_of_prev_attempts': FeatureLabel('Previous attempts at this module', ValueFormat.count),
  'studied_credits': FeatureLabel('Credits being studied', ValueFormat.count),
  'registration_lead_days': FeatureLabel('Days registered before the start', ValueFormat.days),
  'banked_assessment_count': FeatureLabel('Results carried over from an earlier attempt', ValueFormat.count),
  // Benchmark (OULAD) feature set v2 additions
  'active_days_last_14d': FeatureLabel('Days active on the learning platform, last 14 days', ValueFormat.count),
  'quiz_clicks_to_date': FeatureLabel('Quiz activity so far', ValueFormat.count),
  'quiz_clicks_last_7d': FeatureLabel('Quiz activity, last 7 days', ValueFormat.count),
  'quiz_clicks_last_14d': FeatureLabel('Quiz activity, last 14 days', ValueFormat.count),
  'quiz_clicks_last_30d': FeatureLabel('Quiz activity, last 30 days', ValueFormat.count),
  'quiz_trend_14d': FeatureLabel('Change in quiz activity (14-day windows)', ValueFormat.perDay),
  'forum_clicks_to_date': FeatureLabel('Forum activity so far', ValueFormat.count),
  'forum_clicks_last_14d': FeatureLabel('Forum activity, last 14 days', ValueFormat.count),
  'forum_trend_14d': FeatureLabel('Change in forum activity (14-day windows)', ValueFormat.perDay),
  'content_clicks_last_14d': FeatureLabel('Course-content activity, last 14 days', ValueFormat.count),
  'content_trend_14d': FeatureLabel('Change in course-content activity (14-day windows)', ValueFormat.perDay),
  'submissions_last_30d': FeatureLabel('Submissions, last 30 days', ValueFormat.count),
  'completion_rate_last_30d': FeatureLabel('Assessments submitted, last 30 days', ValueFormat.fractionAsPercent),
  'score_trend_per_30d': FeatureLabel('Change in scores per month', ValueFormat.score),
  'score_change_from_first': FeatureLabel('Latest score compared with your first', ValueFormat.score),
  'clicks_last_7d_vs_30d_rate': FeatureLabel('Recent week compared with the last month', ValueFormat.perDay),
  // Institutional feature set inst-fs-1.0.0 additions
  'attendance_rate_last_7d': FeatureLabel('Attendance in the last 7 days', ValueFormat.fractionAsPercent),
  'attendance_rate_last_30d': FeatureLabel('Attendance in the last 30 days', ValueFormat.fractionAsPercent),
  'last_released_score_pct': FeatureLabel('Most recent released score', ValueFormat.score),
  'engagement_events_last_7d': FeatureLabel('Learning-platform activity, last 7 days', ValueFormat.count),
  'engagement_events_last_14d': FeatureLabel('Learning-platform activity, last 14 days', ValueFormat.count),
  'engagement_events_last_30d': FeatureLabel('Learning-platform activity, last 30 days', ValueFormat.count),
  'quiz_attempts_last_30d': FeatureLabel('Quiz attempts, last 30 days', ValueFormat.count),
  'days_since_last_engagement': FeatureLabel('Days since last learning-platform activity', ValueFormat.days),
};

FeatureLabel labelFor(String feature) => featureLabels[feature] ?? FeatureLabel(feature, ValueFormat.raw);

String formatFactorValue(RiskFactor factor) {
  final value = factor.featureValue;
  if (value == null) return 'not available';
  return switch (labelFor(factor.feature).format) {
    ValueFormat.fractionAsPercent => formatPercent(value.toDouble()),
    ValueFormat.count => formatNumber(value, maxDecimals: 0),
    ValueFormat.days => '${formatNumber(value, maxDecimals: 0)} days',
    ValueFormat.score => formatNumber(value, maxDecimals: 1),
    ValueFormat.perDay => '${formatNumber(value, maxDecimals: 1)} per day',
    ValueFormat.gpa => formatNumber(value),
    ValueFormat.raw => formatNumber(value, maxDecimals: 3),
  };
}

String directionText(FactorDirection direction) => switch (direction) {
      FactorDirection.increasesRisk => 'Raised the risk estimate',
      FactorDirection.decreasesRisk => 'Lowered the risk estimate',
    };
