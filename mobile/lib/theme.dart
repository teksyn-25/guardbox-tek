import 'package:flutter/material.dart';

const kBg = Color(0xFF080C18);
const kSurface = Color(0xFF0F1628);
const kCard = Color(0xFF131C30);
const kCardBorder = Color(0xFF1E2D45);
const kAccent = Color(0xFF00E8A0);
const kAccentDim = Color(0x2200E8A0);
const kAccentGlow = Color(0x4400E8A0);
const kDanger = Color(0xFFFF3B4E);
const kDangerDim = Color(0x22FF3B4E);
const kTextPrimary = Color(0xFFFFFFFF);
const kTextSecondary = Color(0xFF6B7FA3);

ThemeData guardBoxTheme() => ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: kBg,
      colorScheme: const ColorScheme.dark(
        primary: kAccent,
        onPrimary: Colors.black,
        surface: kSurface,
        onSurface: kTextPrimary,
        secondary: kAccent,
        onSecondary: Colors.black,
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: kBg,
        elevation: 0,
        scrolledUnderElevation: 0,
        iconTheme: IconThemeData(color: kAccent),
      ),
      cardTheme: CardTheme(
        color: kCard,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: const BorderSide(color: kCardBorder),
        ),
      ),
      floatingActionButtonTheme: const FloatingActionButtonThemeData(
        backgroundColor: kAccent,
        foregroundColor: Colors.black,
        elevation: 4,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: kAccent,
          foregroundColor: Colors.black,
          minimumSize: const Size(double.infinity, 52),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(foregroundColor: kAccent),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: kCard,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: kCardBorder),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: kCardBorder),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: kAccent, width: 1.5),
        ),
        labelStyle: const TextStyle(color: kTextSecondary),
        hintStyle: const TextStyle(color: kTextSecondary),
      ),
      chipTheme: ChipThemeData(
        backgroundColor: kCard,
        side: const BorderSide(color: kCardBorder),
        labelStyle: const TextStyle(color: kTextSecondary, fontSize: 12),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(6)),
      ),
      dividerTheme: const DividerThemeData(color: kCardBorder, thickness: 1),
      iconTheme: const IconThemeData(color: kAccent),
    );
