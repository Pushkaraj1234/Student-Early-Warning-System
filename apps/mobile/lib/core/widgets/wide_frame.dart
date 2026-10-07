import 'package:flutter/material.dart';
import 'package:sews_mobile/core/layout/breakpoints.dart';

/// Centres the app at [Breakpoints.maxFrameWidth] on wide screens (e.g. a desktop browser), so
/// text lines and cards keep a readable width. Narrower windows are passed through unchanged.
class WideFrame extends StatelessWidget {
  const WideFrame({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    final media = MediaQuery.of(context);
    if (media.size.width <= Breakpoints.maxFrameWidth) return child;
    final scheme = Theme.of(context).colorScheme;
    final side = BorderSide(color: scheme.outlineVariant);
    return ColoredBox(
      color: scheme.surfaceContainer,
      child: Center(
        child: DecoratedBox(
          position: DecorationPosition.foreground,
          decoration: BoxDecoration(border: Border(left: side, right: side)),
          child: SizedBox(
            width: Breakpoints.maxFrameWidth,
            // Widgets below measure the frame, not the whole window.
            child: MediaQuery(
              data: media.copyWith(size: Size(Breakpoints.maxFrameWidth, media.size.height)),
              child: ClipRect(child: child),
            ),
          ),
        ),
      ),
    );
  }
}
