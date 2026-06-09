// lib/routing/sovereign_page.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Sovereign page transition: a gentle fade + slight upward rise.
CustomTransitionPage<T> sovereignPage<T>({required Widget child, LocalKey? key}) {
  return CustomTransitionPage<T>(
    key: key,
    transitionDuration: const Duration(milliseconds: 280),
    reverseTransitionDuration: const Duration(milliseconds: 220),
    child: child,
    transitionsBuilder: (context, animation, secondaryAnimation, child) {
      final curved = CurvedAnimation(parent: animation, curve: Curves.easeOutCubic);
      return FadeTransition(
        opacity: curved,
        child: SlideTransition(
          position: Tween<Offset>(begin: const Offset(0, 0.04), end: Offset.zero).animate(curved),
          child: child,
        ),
      );
    },
  );
}
