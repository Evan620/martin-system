// lib/features/profile/presentation/me_screen.dart
//
// "Me" (profile) screen — Sovereign glass design.
//
// Matches the approved mockup (app-shape.html · screen ④ Me):
//   - a glass profile header card with a gold circular avatar ("AD"),
//     name "Amina Diallo" and "Energy TWG · Member";
//   - a "MY ACTION ITEMS" glass card with inner-glass checkbox rows + due dates;
//   - a "REMINDERS" glass card with an inner-glass toggle row;
//   - a "NOTIFICATIONS" settings glass card with inner-glass toggle rows;
//   - a subtle "Sign out" text button at the bottom.
//
// Uses glass-inside-glass throughout: each outer GlassCard holds lighter
// GlassSurface.inner rows/chips so the stack reads as layered depth.
//
// This is the visual build with representative seed content; live data is a
// later pass.
import 'package:flutter/material.dart';

import '../../../core/glass/glass.dart';
import '../../../core/theme/sovereign_colors.dart';

class MeScreen extends StatelessWidget {
  const MeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: SovereignColors.navy,
      body: DecoratedBox(
        // A soft navy gradient so the glass surfaces have something to blur over.
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [
              SovereignColors.navyRaised,
              SovereignColors.navy,
              SovereignColors.navyDeep,
            ],
            stops: [0.0, 0.45, 1.0],
          ),
        ),
        child: SafeArea(
          bottom: false,
          child: SingleChildScrollView(
            // ~104px bottom padding so the floating glass nav never covers content.
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 104),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: const [
                _ProfileHeaderCard(),
                SizedBox(height: 18),
                _ActionItemsCard(),
                SizedBox(height: 18),
                _RemindersCard(),
                SizedBox(height: 18),
                _NotificationsCard(),
                SizedBox(height: 26),
                _SignOutButton(),
                SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Profile header — glass card with a gold avatar + name + role.
// ---------------------------------------------------------------------------
class _ProfileHeaderCard extends StatelessWidget {
  const _ProfileHeaderCard();

  @override
  Widget build(BuildContext context) {
    return const GlassCard(
      padding: EdgeInsets.all(18),
      child: Row(
        children: [
          _GoldAvatar(initials: 'AD'),
          SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Amina Diallo',
                  style: TextStyle(
                    fontFamily: 'Georgia',
                    color: SovereignColors.ivory,
                    fontSize: 22,
                    height: 1.1,
                  ),
                ),
                SizedBox(height: 4),
                Text(
                  'Energy TWG · Member',
                  style: TextStyle(
                    color: SovereignColors.ivory,
                    fontSize: 13,
                    height: 1.2,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _GoldAvatar extends StatelessWidget {
  const _GoldAvatar({required this.initials});

  final String initials;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        gradient: const LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [Color(0xFFE6C766), SovereignColors.gold],
        ),
        boxShadow: [
          BoxShadow(
            color: SovereignColors.gold.withValues(alpha: 0.40),
            blurRadius: 16,
            spreadRadius: 1,
          ),
        ],
      ),
      child: Center(
        child: Text(
          initials,
          style: const TextStyle(
            color: SovereignColors.navy,
            fontSize: 20,
            fontWeight: FontWeight.w700,
            letterSpacing: 0.5,
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// MY ACTION ITEMS — outer glass card, inner-glass checkbox rows + due dates.
// ---------------------------------------------------------------------------
class _ActionItemsCard extends StatelessWidget {
  const _ActionItemsCard();

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          _SectionLabel('MY ACTION ITEMS'),
          SizedBox(height: 12),
          _ActionItemRow(
            label: 'Send budget input',
            trailing: 'Due Tue',
            done: false,
          ),
          SizedBox(height: 10),
          _ActionItemRow(
            label: 'Confirm attendance',
            trailing: 'done',
            done: true,
          ),
        ],
      ),
    );
  }
}

class _ActionItemRow extends StatelessWidget {
  const _ActionItemRow({
    required this.label,
    required this.trailing,
    required this.done,
  });

  final String label;
  final String trailing;
  final bool done;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Icon(
            done ? Icons.check_box_rounded : Icons.check_box_outline_blank_rounded,
            size: 20,
            color: done
                ? SovereignColors.gold
                : SovereignColors.ivory.withValues(alpha: 0.65),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                color: done
                    ? SovereignColors.ivory.withValues(alpha: 0.55)
                    : SovereignColors.ivory,
                fontSize: 14,
                decoration: done ? TextDecoration.lineThrough : null,
                decorationColor: SovereignColors.ivory.withValues(alpha: 0.55),
              ),
            ),
          ),
          const SizedBox(width: 10),
          Text(
            trailing,
            style: TextStyle(
              color: done
                  ? SovereignColors.ivory.withValues(alpha: 0.5)
                  : SovereignColors.gold,
              fontSize: 11.5,
              fontWeight: done ? FontWeight.w400 : FontWeight.w600,
              letterSpacing: 0.3,
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// REMINDERS — outer glass card, inner-glass toggle row.
// ---------------------------------------------------------------------------
class _RemindersCard extends StatelessWidget {
  const _RemindersCard();

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          _SectionLabel('REMINDERS'),
          SizedBox(height: 12),
          _ToggleRow(
            icon: Icons.notifications_active_rounded,
            label: '30 min before sessions',
            value: true,
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// NOTIFICATIONS — settings glass card with a couple of inner-glass toggle rows.
// ---------------------------------------------------------------------------
class _NotificationsCard extends StatelessWidget {
  const _NotificationsCard();

  @override
  Widget build(BuildContext context) {
    return GlassCard(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          _SectionLabel('NOTIFICATIONS'),
          SizedBox(height: 12),
          _ToggleRow(
            icon: Icons.event_available_rounded,
            label: 'Meeting updates',
            value: true,
          ),
          SizedBox(height: 10),
          _ToggleRow(
            icon: Icons.description_rounded,
            label: 'New shared documents',
            value: true,
          ),
          SizedBox(height: 10),
          _ToggleRow(
            icon: Icons.campaign_rounded,
            label: 'Summit announcements',
            value: false,
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shared bits.
// ---------------------------------------------------------------------------

/// Uppercase, gold, letter-spaced section label (matches the mockup `.lab2`).
class _SectionLabel extends StatelessWidget {
  const _SectionLabel(this.text);

  final String text;

  @override
  Widget build(BuildContext context) {
    return Text(
      text,
      style: const TextStyle(
        color: SovereignColors.gold,
        fontSize: 11,
        fontWeight: FontWeight.w600,
        letterSpacing: 1.8,
      ),
    );
  }
}

/// An inner-glass row with a leading icon, label and a (decorative) toggle.
class _ToggleRow extends StatelessWidget {
  const _ToggleRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  final IconData icon;
  final String label;
  final bool value;

  @override
  Widget build(BuildContext context) {
    return GlassSurface.inner(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      child: Row(
        children: [
          Icon(
            icon,
            size: 19,
            color: SovereignColors.gold.withValues(alpha: 0.85),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              label,
              style: const TextStyle(
                color: SovereignColors.ivory,
                fontSize: 14,
              ),
            ),
          ),
          const SizedBox(width: 10),
          _GlassToggle(value: value),
        ],
      ),
    );
  }
}

/// A small Sovereign-styled on/off pill. Decorative in this visual pass —
/// wiring to live settings is a later pass.
class _GlassToggle extends StatelessWidget {
  const _GlassToggle({required this.value});

  final bool value;

  @override
  Widget build(BuildContext context) {
    final track = value
        ? SovereignColors.gold.withValues(alpha: 0.85)
        : SovereignColors.ivory.withValues(alpha: 0.18);
    final knobColor = value ? SovereignColors.navy : SovereignColors.ivory;

    return Container(
      width: 42,
      height: 24,
      padding: const EdgeInsets.all(3),
      decoration: BoxDecoration(
        color: track,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: value
              ? SovereignColors.gold
              : SovereignColors.ivory.withValues(alpha: 0.25),
          width: 1,
        ),
      ),
      child: Align(
        alignment: value ? Alignment.centerRight : Alignment.centerLeft,
        child: Container(
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: knobColor,
          ),
        ),
      ),
    );
  }
}

/// A subtle text-only "Sign out" action at the bottom of the screen.
class _SignOutButton extends StatelessWidget {
  const _SignOutButton();

  @override
  Widget build(BuildContext context) {
    return Center(
      child: TextButton(
        onPressed: () {},
        style: TextButton.styleFrom(
          foregroundColor: SovereignColors.ivory.withValues(alpha: 0.6),
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        ),
        child: const Text(
          'Sign out',
          style: TextStyle(
            fontSize: 13.5,
            letterSpacing: 0.4,
          ),
        ),
      ),
    );
  }
}
