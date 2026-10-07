/// Window widths (logical pixels) at which the layout changes. Values follow the Material 3
/// window size classes (m3.material.io/foundations/layout/applying-layout/window-size-classes).
abstract final class Breakpoints {
  /// From this width ("medium" and up) the main sections use a side navigation rail
  /// instead of the bottom navigation bar.
  static const double navigationRail = 600;

  /// Widest the app is drawn; wider browser windows show it centred.
  static const double maxFrameWidth = 1200;
}
