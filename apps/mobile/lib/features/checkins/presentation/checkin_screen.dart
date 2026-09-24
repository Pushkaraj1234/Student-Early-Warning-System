import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:sews_mobile/core/app_providers.dart';
import 'package:sews_mobile/core/data_providers.dart';
import 'package:sews_mobile/core/errors/app_failure.dart';
import 'package:sews_mobile/features/checkins/domain/checkin.dart';

/// Optional check-in: practical study needs and whether the student would like contact.
class CheckinScreen extends ConsumerStatefulWidget {
  const CheckinScreen({super.key});

  @override
  ConsumerState<CheckinScreen> createState() => _CheckinScreenState();
}

class _CheckinScreenState extends ConsumerState<CheckinScreen> {
  final Set<SupportNeed> _needs = {};
  final TextEditingController _comment = TextEditingController();
  bool _wantsContact = false;
  bool _submitting = false;
  String? _error;

  @override
  void dispose() {
    _comment.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    final draft = CheckinDraft(needs: _needs, wantsContact: _wantsContact, comment: _comment.text);
    final problem = draft.validationError;
    if (problem != null) {
      setState(() => _error = problem);
      return;
    }
    setState(() {
      _submitting = true;
      _error = null;
    });
    try {
      final studentId = await ref.read(currentStudentIdProvider.future);
      await ref.read(checkinsRepositoryProvider).submit(studentId, draft);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Thanks. Your check-in was sent to your mentor.')),
      );
      context.pop();
    } on AppFailure catch (failure) {
      if (mounted) setState(() => _error = failure.message);
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Scaffold(
      appBar: AppBar(title: const Text('Check in')),
      body: SafeArea(
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text('Is anything getting in the way of your studies?', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              'This is optional. Your mentor sees your answers and can offer support. '
              'It is not a health or mental-health assessment.',
              style: theme.textTheme.bodySmall,
            ),
            const SizedBox(height: 8),
            for (final need in SupportNeed.values)
              CheckboxListTile(
                contentPadding: EdgeInsets.zero,
                value: _needs.contains(need),
                title: Text(need.label),
                onChanged: _submitting
                    ? null
                    : (checked) => setState(() => checked == true ? _needs.add(need) : _needs.remove(need)),
              ),
            SwitchListTile(
              contentPadding: EdgeInsets.zero,
              value: _wantsContact,
              title: const Text('I would like my mentor to contact me'),
              onChanged: _submitting ? null : (value) => setState(() => _wantsContact = value),
            ),
            TextField(
              controller: _comment,
              enabled: !_submitting,
              maxLength: maxCheckinCommentLength,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Anything else? (optional)',
                helperText: 'Avoid sharing medical details here.',
              ),
            ),
            if (_error != null) ...[
              const SizedBox(height: 8),
              Text(_error!, style: TextStyle(color: theme.colorScheme.error)),
            ],
            const SizedBox(height: 16),
            FilledButton(
              onPressed: _submitting ? null : _submit,
              child: _submitting
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : const Text('Send check-in'),
            ),
          ],
        ),
      ),
    );
  }
}
