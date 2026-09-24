import 'package:intl/intl.dart';

final DateFormat _date = DateFormat('d MMM yyyy');
final DateFormat _dateTime = DateFormat('d MMM yyyy, HH:mm');

String formatDate(DateTime value) => _date.format(value.toLocal());

String formatDateTime(DateTime value) => _dateTime.format(value.toLocal());

/// 0.724 -> "72%". Rates are fractions in [0, 1].
String formatPercent(double rate) => '${(rate * 100).round()}%';

/// Trims trailing zeros: 8.50 -> "8.5", 15.0 -> "15".
String formatNumber(num value, {int maxDecimals = 2}) {
  final fixed = value.toStringAsFixed(maxDecimals);
  return fixed.contains('.') ? fixed.replaceFirst(RegExp(r'\.?0+$'), '') : fixed;
}

String formatScore(num score, num maxScore) => '${formatNumber(score)} / ${formatNumber(maxScore)}';
