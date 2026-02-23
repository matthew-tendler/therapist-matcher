/**
 * Therapist Matcher — Google Sheets Companion
 *
 * HOW TO USE:
 *   1. In your Google Sheet, go to Extensions > Apps Script
 *   2. Delete any existing code and paste this entire file
 *   3. Click Save, then Run > createMatcherTab
 *   4. Approve permissions when prompted
 *   5. Switch to the new "Matcher" tab — done
 *
 * Re-run any time to reset the Matcher tab to its default state.
 *
 * ASSUMES the data tab is named exactly: "Therapist List"
 * Column layout (do not change column order in Therapist List):
 *   A  Therapist       B  Min Age       C  Conditions     D  Approaches
 *   E  Exclusions      F  EMDR          G  Modality       H  In-Person Days
 *   I  Location        J  Availability  K  Notes          L  Last Updated
 *   M  Updated By      N  Str. Medicaid O  Medicare       P  Fidelis
 *   Q  Healthfirst     R  NWD           S  BCBS           T  Cigna
 *   U  Optum           V  Aetna         W  1199
 */

function createMatcherTab() {
  const ss = SpreadsheetApp.getActiveSpreadsheet();

  // Verify data sheet exists
  const dataSheet = ss.getSheetByName("Therapist List");
  if (!dataSheet) {
    SpreadsheetApp.getUi().alert(
      '❌ Could not find a tab named "Therapist List".\n\n' +
      'Rename your data tab to exactly "Therapist List" and run again.'
    );
    return;
  }

  // Create (or reset) Matcher tab
  let sheet = ss.getSheetByName("Matcher");
  if (sheet) ss.deleteSheet(sheet);
  sheet = ss.insertSheet("Matcher");

  // Put Matcher right after Therapist List
  const listIndex = ss.getSheets().indexOf(dataSheet);
  ss.moveActiveSheet(listIndex + 2);

  sheet.clearFormats();


  // ─── HEADER ────────────────────────────────────────────────────────────────

  sheet.setRowHeight(1, 50);
  const header = sheet.getRange("A1:K1");
  header.merge()
    .setValue("🔍  Therapist Matcher")
    .setFontSize(20).setFontWeight("bold")
    .setBackground("#1e3a5f").setFontColor("#ffffff")
    .setHorizontalAlignment("center").setVerticalAlignment("middle");


  // ─── SEARCH CRITERIA (rows 2–8) ────────────────────────────────────────────

  const fields = [
    { row: 2, label: "Insurance",             hint: "Select an insurance plan",         default: "Any"            },
    { row: 3, label: "Modality",              hint: "In-Person / Telehealth / Hybrid",  default: "Any"            },
    { row: 4, label: "Location",              hint: "Only applies to In-Person/Hybrid", default: "Any"            },
    { row: 5, label: "Patient Age (0 = any)", hint: "Enter patient's age to filter min-age restrictions", default: 0 },
    { row: 6, label: "Condition Keyword",     hint: "e.g.  anxiety   OCD   trauma   ADHD  (one term at a time)", default: "" },
    { row: 7, label: "EMDR Required",         hint: "Filter to only EMDR-trained therapists", default: "Any"      },
    { row: 8, label: "Availability",          hint: "",                                 default: "Available only" },
  ];

  const LABEL_BG  = "#eef2fb";
  const INPUT_BG  = "#ffffff";
  const HINT_FG   = "#888888";
  const BORDER_C  = "#c5d0e8";
  const ACCENT_C  = "#4a7fc1";
  const solid     = SpreadsheetApp.BorderStyle.SOLID;
  const medium    = SpreadsheetApp.BorderStyle.SOLID_MEDIUM;

  fields.forEach(f => {
    // Label cell (A)
    sheet.getRange(`A${f.row}`)
      .setValue(f.label)
      .setBackground(LABEL_BG).setFontWeight("bold").setFontSize(10)
      .setVerticalAlignment("middle")
      .setBorder(true, true, true, true, null, null, BORDER_C, solid);

    // Input cell (B)
    sheet.getRange(`B${f.row}`)
      .setValue(f.default)
      .setBackground(INPUT_BG).setFontSize(11)
      .setHorizontalAlignment("left").setVerticalAlignment("middle")
      .setBorder(true, true, true, true, null, null, ACCENT_C, medium);

    // Hint (C)
    if (f.hint) {
      sheet.getRange(`C${f.row}`)
        .setValue(f.hint)
        .setFontSize(9).setFontColor(HINT_FG).setFontStyle("italic")
        .setVerticalAlignment("middle");
      sheet.getRange(`C${f.row}:F${f.row}`).merge();
    }

    sheet.setRowHeight(f.row, 32);
  });

  // ── Dropdowns ──
  const dv = (list) =>
    SpreadsheetApp.newDataValidation()
      .requireValueInList(list, true)
      .setAllowInvalid(false)
      .build();

  sheet.getRange("B2").setDataValidation(dv([
    "Any","Straight Medicaid","Medicare","Fidelis","Healthfirst",
    "NWD","BCBS","Cigna","Optum","Aetna","1199"
  ]));
  sheet.getRange("B3").setDataValidation(dv(["Any","In-Person","Telehealth","Hybrid"]));
  sheet.getRange("B4").setDataValidation(dv(["Any","Commack","Jericho","Ronkonkoma"]));
  sheet.getRange("B7").setDataValidation(dv(["Any","Required"]));
  sheet.getRange("B8").setDataValidation(dv(["Available only","Show all"]));


  // ─── COLUMN WIDTHS ─────────────────────────────────────────────────────────

  sheet.setColumnWidth(1, 195);   // A  label
  sheet.setColumnWidth(2, 195);   // B  input
  sheet.setColumnWidth(3, 30);    // C  spacer (hints merged into D-F)
  sheet.setColumnWidth(4, 120);
  sheet.setColumnWidth(5, 120);
  sheet.setColumnWidth(6, 120);


  // ─── THIN SEPARATOR ────────────────────────────────────────────────────────

  sheet.setRowHeight(9, 6);
  sheet.getRange("A9:K9").setBackground("#1e3a5f");


  // ─── RESULTS SECTION ───────────────────────────────────────────────────────

  // "Results" label
  sheet.setRowHeight(10, 28);
  sheet.getRange("A10")
    .setValue("RESULTS — updates automatically when you change any filter above")
    .setFontWeight("bold").setFontSize(10).setFontColor("#1e3a5f")
    .setBackground("#dce8f7").setVerticalAlignment("middle");
  sheet.getRange("A10:K10").merge().setBackground("#dce8f7");

  // Column headers for results (row 11)
  const resultHeaders = [
    ["A", "Therapist",     240],
    ["B", "Min Age",        65],
    ["C", "Modality",       90],
    ["D", "In-Person Days", 130],
    ["E", "Location",      100],
    ["F", "Availability",  110],
    ["G", "Conditions",    220],
    ["H", "Approaches",    180],
    ["I", "EMDR",           60],
    ["J", "Notes",         220],
    ["K", "Exclusions",    160],
  ];

  sheet.setRowHeight(11, 26);
  resultHeaders.forEach(([col, label, width]) => {
    sheet.getRange(`${col}11`)
      .setValue(label)
      .setFontWeight("bold").setFontSize(10)
      .setBackground("#dce8f7").setFontColor("#1e3a5f")
      .setHorizontalAlignment("center").setVerticalAlignment("middle")
      .setBorder(true, true, true, true, null, null, "#aec6e8", solid);
    sheet.setColumnWidth(col.charCodeAt(0) - 64, width);
  });


  // ─── FILTER FORMULA ────────────────────────────────────────────────────────
  //
  // Column mapping in "Therapist List":
  //   A  Therapist     B  Min Age    C  Conditions  D  Approaches   E  Exclusions
  //   F  EMDR          G  Modality   H  IP Days      I  Location     J  Availability
  //   K  Notes         N  Str.Med    O  Medicare     P  Fidelis       Q  Healthfirst
  //   R  NWD           S  BCBS       T  Cigna        U  Optum         V  Aetna
  //   W  1199
  //
  // Modality logic:
  //   "In-Person"  → show In-Person AND Hybrid
  //   "Telehealth" → show Telehealth AND Hybrid
  //   "Hybrid"     → show Hybrid only
  //   "Any"        → show all
  //
  // FILTER needs all conditions as same-length TRUE/FALSE arrays.
  // Boolean addition (a)+(b) returns 1 if either is true — truthy in FILTER.

  const formula = [
    `=IFERROR(`,
    `  FILTER(`,
    `    CHOOSE({1,2,3,4,5,6,7,8,9,10,11},`,
    `      'Therapist List'!A2:A,`,
    `      'Therapist List'!B2:B,`,
    `      'Therapist List'!G2:G,`,
    `      'Therapist List'!H2:H,`,
    `      'Therapist List'!I2:I,`,
    `      'Therapist List'!J2:J,`,
    `      'Therapist List'!C2:C,`,
    `      'Therapist List'!D2:D,`,
    `      'Therapist List'!F2:F,`,
    `      'Therapist List'!K2:K,`,
    `      'Therapist List'!E2:E`,
    `    ),`,
    // Availability filter
    `    IF(B8="Available only",'Therapist List'!J2:J="Available",TRUE),`,
    // Insurance filter (maps dropdown label -> correct column)
    `    IF(B2="Any",TRUE,`,
    `      IF(B2="Straight Medicaid",'Therapist List'!N2:N="Yes",`,
    `      IF(B2="Medicare",'Therapist List'!O2:O="Yes",`,
    `      IF(B2="Fidelis",'Therapist List'!P2:P="Yes",`,
    `      IF(B2="Healthfirst",'Therapist List'!Q2:Q="Yes",`,
    `      IF(B2="NWD",'Therapist List'!R2:R="Yes",`,
    `      IF(B2="BCBS",'Therapist List'!S2:S="Yes",`,
    `      IF(B2="Cigna",'Therapist List'!T2:T="Yes",`,
    `      IF(B2="Optum",'Therapist List'!U2:U="Yes",`,
    `      IF(B2="Aetna",'Therapist List'!V2:V="Yes",`,
    `      IF(B2="1199",'Therapist List'!W2:W="Yes",`,
    `      TRUE))))))))))),`,
    // Modality filter (Hybrid satisfies both In-Person and Telehealth)
    `    IF(B3="Any",TRUE,`,
    `      IF(B3="In-Person",('Therapist List'!G2:G="In-Person")+('Therapist List'!G2:G="Hybrid"),`,
    `      IF(B3="Telehealth",('Therapist List'!G2:G="Telehealth")+('Therapist List'!G2:G="Hybrid"),`,
    `      'Therapist List'!G2:G=B3))),`,
    // Location filter (SEARCH handles "Commack, Jericho" multi-location cells)
    `    IF(B4="Any",TRUE,ISNUMBER(SEARCH(B4,'Therapist List'!I2:I))),`,
    // Age filter (0 = skip; therapists with no min age (0) always pass)
    `    IF(B5=0,TRUE,('Therapist List'!B2:B=0)+('Therapist List'!B2:B<=B5)),`,
    // Condition keyword (searches both Conditions and Approaches columns)
    `    IF(B6="",TRUE,ISNUMBER(SEARCH(LOWER(B6),LOWER('Therapist List'!C2:C)&" "&LOWER('Therapist List'!D2:D)))),`,
    // EMDR filter
    `    IF(B7="Any",TRUE,'Therapist List'!F2:F="Yes")`,
    `  ),`,
    `  "— No matches. Try setting some filters to Any —"`,
    `)`,
  ].join(" ");

  sheet.getRange("A12").setFormula(formula);

  // ── Diagnostic cell: confirm data sheet is readable ──
  // Shows therapist count in H9 so you can verify the reference is live
  sheet.getRange("H9")
    .setFormula(`=COUNTA('Therapist List'!A2:A)&" therapists loaded"`)
    .setFontSize(9).setFontColor("#888888").setHorizontalAlignment("right");
  sheet.getRange("H9:K9").merge();

  // Alternating row shading — batched into a single API call (much faster)
  const numResultRows = 49;
  const bgColors = Array.from({ length: numResultRows }, (_, i) =>
    Array(11).fill(i % 2 === 0 ? "#ffffff" : "#f4f8fe")
  );
  const resultRange = sheet.getRange(12, 1, numResultRows, 11);
  resultRange.setBackgrounds(bgColors).setFontSize(10).setVerticalAlignment("middle");
  sheet.setRowHeightsForced(12, numResultRows, 22);


  // ─── FREEZE & FINAL TOUCHES ────────────────────────────────────────────────

  sheet.setFrozenRows(11);       // freeze through column header row

  // Hide gridlines for a cleaner look
  sheet.setHiddenGridlines(true);

  // Protect the formula cell so it isn't accidentally deleted
  const protection = sheet.getRange("A12:K60").protect();
  protection.setDescription("Matcher results — do not edit manually");
  protection.setWarningOnly(true);   // warns but doesn't block (no hard lock)

  SpreadsheetApp.flush();

  SpreadsheetApp.getUi().alert(
    "✅ Matcher tab ready!\n\n" +
    "Use the dropdowns in column B to filter therapists.\n" +
    "Results in the table below update instantly.\n\n" +
    "Tip: set all filters to 'Any' / 0 / blank to see everyone who's Available."
  );
}
