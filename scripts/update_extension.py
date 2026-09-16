# -*- coding: utf-8 -*-
"""
Full updater and builder for Quran LibreOffice Extension:
- Academic Citation Format: قَالَ تَعَالَى: ﴿ ... ﴾ [اسم السورة: الآيات]
- Authentic KFGQPC ornate Quran brackets (U+FD5F on right, U+FD5E on left)
- Full event listeners for Qala Taala and Reference checkboxes
- Rebuild quran_libreoffice.oxt
"""
import os
import zipfile
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_DIR = os.path.join(BASE_DIR, "extension")

# 1. GENERATE QuranDialog.xdl
xdl_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE dlg:window PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "dialog.dtd">
<dlg:window xmlns:dlg="http://openoffice.org/2000/dialog" xmlns:script="http://openoffice.org/2000/script"
            dlg:id="QuranDialog" dlg:left="60" dlg:top="40" dlg:width="440" dlg:height="330"
            dlg:closeable="true" dlg:moveable="true" dlg:title="إدراج القرآن الكريم بالرسم العثماني">
 <dlg:bulletinboard>

  <!-- Title Header -->
  <dlg:text dlg:id="lbl_title" dlg:left="10" dlg:top="6" dlg:width="420" dlg:height="16"
            dlg:value="مصحف المدينة النبوية - مجمع الملك فهد لطباعة المصحف الشريف" dlg:align="center"/>

  <!-- Section 1: Selection & Search Header -->
  <dlg:text dlg:id="lbl_sec1" dlg:left="15" dlg:top="26" dlg:width="410" dlg:height="14"
            dlg:value="اختيار السورة والآيات" dlg:align="right"/>
  <dlg:fixedline dlg:id="sep1" dlg:left="15" dlg:top="40" dlg:width="410" dlg:height="2"/>

  <!-- Row 1: Surah Selection (Right) & Search Prompt (Left) -->
  <dlg:text dlg:id="lbl_surah" dlg:left="380" dlg:top="48" dlg:width="45" dlg:height="14"
            dlg:value="السورة:" dlg:align="right"/>
  <dlg:menulist dlg:id="lst_surah" dlg:left="200" dlg:top="46" dlg:width="175" dlg:height="16" dlg:spin="true"/>

  <dlg:text dlg:id="lbl_search" dlg:left="15" dlg:top="48" dlg:width="170" dlg:height="14"
            dlg:value="بحث سريع في الآيات:" dlg:align="right"/>

  <!-- Row 2: Ayah Range (Right) & Search Inputs (Left) -->
  <dlg:text dlg:id="lbl_from" dlg:left="380" dlg:top="70" dlg:width="45" dlg:height="14"
            dlg:value="من آية:" dlg:align="right"/>
  <dlg:numericfield dlg:id="num_from" dlg:left="315" dlg:top="68" dlg:width="60" dlg:height="16"
                    dlg:spin="true" dlg:decimal-accuracy="0" dlg:value-min="1" dlg:value-max="286" dlg:value="1"/>

  <dlg:text dlg:id="lbl_to" dlg:left="275" dlg:top="70" dlg:width="35" dlg:height="14"
            dlg:value="إلى:" dlg:align="right"/>
  <dlg:numericfield dlg:id="num_to" dlg:left="200" dlg:top="68" dlg:width="70" dlg:height="16"
                    dlg:spin="true" dlg:decimal-accuracy="0" dlg:value-min="1" dlg:value-max="286" dlg:value="7"/>

  <dlg:textfield dlg:id="txt_search" dlg:left="65" dlg:top="68" dlg:width="120" dlg:height="16" dlg:align="right"/>
  <dlg:button dlg:id="btn_search" dlg:left="15" dlg:top="68" dlg:width="45" dlg:height="16" dlg:value="بحث"/>

  <!-- Row 3: Search Results Dropdown -->
  <dlg:menulist dlg:id="lst_search" dlg:left="15" dlg:top="90" dlg:width="410" dlg:height="16" dlg:spin="true"/>

  <!-- Section 2: Formatting & Citation Options -->
  <dlg:text dlg:id="lbl_sec2" dlg:left="15" dlg:top="114" dlg:width="410" dlg:height="14"
            dlg:value="خيارات التنسيق والعزو والخط" dlg:align="right"/>
  <dlg:fixedline dlg:id="sep2" dlg:left="15" dlg:top="128" dlg:width="410" dlg:height="2"/>

  <!-- Row 4: Qala Taala, Reference Citation, and Ornate Brackets -->
  <dlg:checkbox dlg:id="chk_qala" dlg:left="305" dlg:top="134" dlg:width="120" dlg:height="16"
                dlg:value="إضافة «قَالَ تَعَالَى»" dlg:checked="true"/>
  <dlg:checkbox dlg:id="chk_reference" dlg:left="160" dlg:top="134" dlg:width="135" dlg:height="16"
                dlg:value="عزو الآيات [السورة: 1-4]" dlg:checked="true"/>
  <dlg:checkbox dlg:id="chk_brackets" dlg:left="15" dlg:top="134" dlg:width="135" dlg:height="16"
                dlg:value="أقواس المصحف المزخرفة" dlg:checked="true"/>

  <!-- Row 5: Basmalah, Newline, and Optional Standalone Header -->
  <dlg:checkbox dlg:id="chk_basmalah" dlg:left="320" dlg:top="154" dlg:width="105" dlg:height="16"
                dlg:value="إدراج البسملة" dlg:checked="true"/>
  <dlg:checkbox dlg:id="chk_newline" dlg:left="175" dlg:top="154" dlg:width="135" dlg:height="16"
                dlg:value="كل آية في سطر مستقل" dlg:checked="false"/>
  <dlg:checkbox dlg:id="chk_header" dlg:left="15" dlg:top="154" dlg:width="150" dlg:height="16"
                dlg:value="سطر عنوان أعلى الآيات" dlg:checked="false"/>

  <!-- Row 6: Font Size and Details -->
  <dlg:text dlg:id="lbl_font" dlg:left="360" dlg:top="174" dlg:width="65" dlg:height="14"
            dlg:value="حجم الخط:" dlg:align="right"/>
  <dlg:numericfield dlg:id="num_fontsize" dlg:left="300" dlg:top="172" dlg:width="55" dlg:height="16"
                    dlg:spin="true" dlg:decimal-accuracy="0" dlg:value="20" dlg:value-min="12" dlg:value-max="72"/>
  <dlg:text dlg:id="lbl_finfo" dlg:left="15" dlg:top="174" dlg:width="275" dlg:height="14"
            dlg:value="الخط: خط مجمع الملك فهد بالرسم العثماني" dlg:align="right"/>

  <!-- Section 3: Live Preview -->
  <dlg:text dlg:id="lbl_sec3" dlg:left="15" dlg:top="194" dlg:width="410" dlg:height="14"
            dlg:value="معاينة النص القرآني" dlg:align="right"/>
  <dlg:fixedline dlg:id="sep3" dlg:left="15" dlg:top="206" dlg:width="410" dlg:height="2"/>

  <dlg:textfield dlg:id="txt_preview" dlg:left="15" dlg:top="212" dlg:width="410" dlg:height="74"
                 dlg:align="right" dlg:multiline="true" dlg:vscroll="true"/>

  <!-- Bottom Action Buttons -->
  <dlg:button dlg:id="btn_insert" dlg:left="270" dlg:top="294" dlg:width="155" dlg:height="24"
              dlg:value="إدراج في المستند" dlg:button-type="ok" dlg:default="true"/>
  <dlg:button dlg:id="btn_cancel" dlg:left="15" dlg:top="294" dlg:width="80" dlg:height="24"
              dlg:value="إلغاء" dlg:button-type="cancel"/>

 </dlg:bulletinboard>
</dlg:window>'''

xdl_path = os.path.join(EXT_DIR, "QuranBasic", "QuranDialog.xdl")
with open(xdl_path, "w", encoding="utf-8") as f:
    f.write(xdl_content)
print(f"Written: {xdl_path}")

# 2. GENERATE QuranModule.xba
basic_source = '''REM  *****  BASIC  *****

Public oDialog As Object
Public aSurahCounts(114) As Long
Public oJobService As Object

' Global variables to safely retain selections
Public g_sura_no As Integer
Public g_from_ayah As Long
Public g_to_ayah As Long
Public g_font_size As Double
Public g_basmalah As Boolean
Public g_header As Boolean
Public g_newline As Boolean
Public g_brackets As Boolean
Public g_qala As Boolean
Public g_reference As Boolean

Sub InsertQuran
    On Error GoTo ErrHandler
    InitSurahCounts()

    ' Default state matching Image 2
    g_sura_no = 1
    g_from_ayah = 1
    g_to_ayah = 7
    g_font_size = 20.0
    g_basmalah = True
    g_header = False
    g_newline = False
    g_brackets = True
    g_qala = True
    g_reference = True

    If GlobalScope.DialogLibraries.hasByName("QuranBasic") Then
        If Not GlobalScope.DialogLibraries.isLibraryLoaded("QuranBasic") Then
            GlobalScope.DialogLibraries.loadLibrary("QuranBasic")
        End If
        oDialog = CreateUnoDialog(GlobalScope.DialogLibraries.QuranBasic.QuranDialog)
    ElseIf DialogLibraries.hasByName("QuranBasic") Then
        If Not DialogLibraries.isLibraryLoaded("QuranBasic") Then
            DialogLibraries.loadLibrary("QuranBasic")
        End If
        oDialog = CreateUnoDialog(DialogLibraries.QuranBasic.QuranDialog)
    Else
        MsgBox "مكتبة الحوار QuranBasic غير موجودة", 16, "خطأ"
        Exit Sub
    End If

    If IsNull(oDialog) Then
        MsgBox "تعذر فتح نافذة القرآن الكريم", 16, "خطأ"
        Exit Sub
    End If

    ' Connect to Python Quran UNO Service
    oJobService = CreateUnoService("org.quran.libreoffice.Job")

    ' Populate 114 Surahs
    Dim aNames(113) As String
    PopulateSurahNames(aNames)

    Dim oLst As Object
    oLst = oDialog.getControl("lst_surah")
    oLst.addItems(aNames, 0)
    oLst.selectItemPos(0, True)

    oDialog.getControl("num_from").setValue(1)
    oDialog.getControl("num_to").setValue(7)
    oDialog.getControl("num_from").getModel().ValueMax = 7
    oDialog.getControl("num_to").getModel().ValueMax = 7

    ' Set preview font if available and right alignment + RTL writing mode
    On Error Resume Next
    oDialog.getControl("txt_preview").getModel().FontName = "KFGQPC_HAFS_Uthmanic_Script_H"
    oDialog.getControl("txt_preview").getModel().FontHeight = 14
    oDialog.getControl("txt_preview").getModel().Align = 2
    oDialog.getControl("txt_preview").getModel().WritingMode = 1
    oDialog.getControl("txt_search").getModel().Align = 2
    oDialog.getControl("txt_search").getModel().WritingMode = 1
    On Error GoTo ErrHandler

    ' Attach Listeners
    Dim oSurahListener As Object
    oSurahListener = CreateUnoListener("SurahEvt_", "com.sun.star.awt.XItemListener")
    oLst.addItemListener(oSurahListener)

    Dim oSearchBtnListener As Object
    oSearchBtnListener = CreateUnoListener("SearchBtn_", "com.sun.star.awt.XActionListener")
    oDialog.getControl("btn_search").addActionListener(oSearchBtnListener)

    Dim oSearchLstListener As Object
    oSearchLstListener = CreateUnoListener("SearchLst_", "com.sun.star.awt.XItemListener")
    oDialog.getControl("lst_search").addItemListener(oSearchLstListener)

    Dim oOptListener As Object
    oOptListener = CreateUnoListener("OptEvt_", "com.sun.star.awt.XItemListener")
    oDialog.getControl("chk_qala").addItemListener(oOptListener)
    oDialog.getControl("chk_reference").addItemListener(oOptListener)
    oDialog.getControl("chk_brackets").addItemListener(oOptListener)
    oDialog.getControl("chk_basmalah").addItemListener(oOptListener)
    oDialog.getControl("chk_header").addItemListener(oOptListener)
    oDialog.getControl("chk_newline").addItemListener(oOptListener)

    Dim oNumListener As Object
    oNumListener = CreateUnoListener("NumEvt_", "com.sun.star.awt.XTextListener")
    oDialog.getControl("num_from").addTextListener(oNumListener)
    oDialog.getControl("num_to").addTextListener(oNumListener)

    ' Initial live preview
    UpdatePreview()

    ' Display modal dialog
    Dim nRes As Integer
    nRes = oDialog.execute()
    If nRes = 1 Then
        ' User confirmed insertion
        PerformInsertion()
    End If
    oDialog.dispose()
    Exit Sub

ErrHandler:
    MsgBox "حدث تنبيه في إضافة القرآن: " & Error$, 16, "تنبيه"
End Sub

Sub SurahEvt_itemStateChanged(oEvt As Object)
    On Error Resume Next
    Dim oLst As Object
    oLst = oDialog.getControl("lst_surah")
    Dim nIdx As Integer
    nIdx = oLst.getSelectedItemPos()
    If nIdx < 0 Then Exit Sub
    Dim sNo As Integer
    sNo = nIdx + 1
    g_sura_no = sNo

    Dim maxAyah As Long
    maxAyah = aSurahCounts(sNo)
    If maxAyah <= 0 Then maxAyah = 7

    Dim oFrom As Object, oTo As Object
    oFrom = oDialog.getControl("num_from")
    oTo = oDialog.getControl("num_to")
    oFrom.getModel().ValueMax = CDbl(maxAyah)
    oTo.getModel().ValueMax = CDbl(maxAyah)
    oFrom.setValue(1)
    oTo.setValue(maxAyah)
    g_from_ayah = 1
    g_to_ayah = maxAyah

    If sNo = 9 Then
        oDialog.getControl("chk_basmalah").setState(0)
        g_basmalah = False
    Else
        oDialog.getControl("chk_basmalah").setState(1)
        g_basmalah = True
    End If

    UpdatePreview()
End Sub
Sub SurahEvt_disposing(oEvt As Object)
End Sub

Sub SearchBtn_actionPerformed(oEvt As Object)
    On Error Resume Next
    Dim q As String
    q = Trim(oDialog.getControl("txt_search").getText())
    If Len(q) = 0 Then Exit Sub

    If IsNull(oJobService) Then
        oJobService = CreateUnoService("org.quran.libreoffice.Job")
    End If
    If IsNull(oJobService) Then
        MsgBox "خدمة القرآن غير متوفرة", 16, "خطأ"
        Exit Sub
    End If

    Dim args(1) As Object
    args(0) = CreateUnoStruct("com.sun.star.beans.NamedValue")
    args(0).Name = "action"
    args(0).Value = "search"
    args(1) = CreateUnoStruct("com.sun.star.beans.NamedValue")
    args(1).Name = "query"
    args(1).Value = q

    Dim vRes
    vRes = oJobService.execute(args)
    Dim oLst As Object
    oLst = oDialog.getControl("lst_search")
    oLst.removeItems(0, oLst.getItemCount())
    If IsArray(vRes) Then
        If UBound(vRes) >= LBound(vRes) Then
            oLst.addItems(vRes, 0)
            oLst.selectItemPos(0, True)
            SelectSearchResult()
        Else
            Dim aEmpty(0) As String
            aEmpty(0) = "لم يتم العثور على نتائج مطابقة"
            oLst.addItems(aEmpty, 0)
        End If
    End If
End Sub
Sub SearchBtn_disposing(oEvt As Object)
End Sub

Sub SearchLst_itemStateChanged(oEvt As Object)
    SelectSearchResult()
End Sub
Sub SearchLst_disposing(oEvt As Object)
End Sub

Sub SelectSearchResult()
    On Error Resume Next
    Dim oLstSearch As Object
    oLstSearch = oDialog.getControl("lst_search")
    Dim selText As String
    selText = oLstSearch.getSelectedItem()
    If Len(selText) = 0 Or Left(selText, 2) = "لم" Then Exit Sub

    Dim parts() As String
    parts = Split(selText, " - ")
    If UBound(parts) >= 0 Then
        Dim subp() As String
        subp = Split(parts(0), ":")
        If UBound(subp) >= 1 Then
            Dim sNo As Integer, aNo As Long
            sNo = CInt(subp(0))
            aNo = CLng(subp(1))
            If sNo >= 1 And sNo <= 114 Then
                g_sura_no = sNo
                oDialog.getControl("lst_surah").selectItemPos(sNo - 1, True)
                Dim maxAyah As Long
                maxAyah = aSurahCounts(sNo)
                oDialog.getControl("num_from").getModel().ValueMax = CDbl(maxAyah)
                oDialog.getControl("num_to").getModel().ValueMax = CDbl(maxAyah)
                oDialog.getControl("num_from").setValue(aNo)
                oDialog.getControl("num_to").setValue(aNo)
                g_from_ayah = aNo
                g_to_ayah = aNo
                UpdatePreview()
            End If
        End If
    End If
End Sub

Sub OptEvt_itemStateChanged(oEvt As Object)
    UpdatePreview()
End Sub
Sub OptEvt_disposing(oEvt As Object)
End Sub

Sub NumEvt_textChanged(oEvt As Object)
    UpdatePreview()
End Sub
Sub NumEvt_disposing(oEvt As Object)
End Sub

Sub UpdatePreview()
    On Error Resume Next
    Dim sNo As Integer
    sNo = oDialog.getControl("lst_surah").getSelectedItemPos() + 1
    If sNo <= 0 Then sNo = 1
    g_sura_no = sNo

    Dim fAya As Long, tAya As Long
    fAya = CLng(oDialog.getControl("num_from").getValue())
    tAya = CLng(oDialog.getControl("num_to").getValue())
    If fAya < 1 Then fAya = 1
    If tAya < fAya Then tAya = fAya
    g_from_ayah = fAya
    g_to_ayah = tAya

    Dim bBasmalah As Boolean, bHeader As Boolean, bNewline As Boolean
    Dim bBrackets As Boolean, bQala As Boolean, bReference As Boolean

    bQala = (oDialog.getControl("chk_qala").getState() = 1)
    bReference = (oDialog.getControl("chk_reference").getState() = 1)
    bBrackets = (oDialog.getControl("chk_brackets").getState() = 1)
    bBasmalah = (oDialog.getControl("chk_basmalah").getState() = 1)
    bHeader = (oDialog.getControl("chk_header").getState() = 1)
    bNewline = (oDialog.getControl("chk_newline").getState() = 1)

    g_qala = bQala
    g_reference = bReference
    g_brackets = bBrackets
    g_basmalah = bBasmalah
    g_header = bHeader
    g_newline = bNewline

    Dim fSize As Double
    fSize = oDialog.getControl("num_fontsize").getValue()
    If fSize > 0 Then g_font_size = fSize

    If IsNull(oJobService) Then
        oJobService = CreateUnoService("org.quran.libreoffice.Job")
    End If
    If Not IsNull(oJobService) Then
        Dim args(9) As Object
        Dim i As Integer
        For i = 0 To 9
            args(i) = CreateUnoStruct("com.sun.star.beans.NamedValue")
        Next i
        args(0).Name = "action"
        args(0).Value = "preview"
        args(1).Name = "sura_no"
        args(1).Value = sNo
        args(2).Name = "from_ayah"
        args(2).Value = fAya
        args(3).Name = "to_ayah"
        args(3).Value = tAya
        args(4).Name = "basmalah"
        args(4).Value = bBasmalah
        args(5).Name = "header"
        args(5).Value = bHeader
        args(6).Name = "newline"
        args(6).Value = bNewline
        args(7).Name = "brackets"
        args(7).Value = bBrackets
        args(8).Name = "qala"
        args(8).Value = bQala
        args(9).Name = "reference"
        args(9).Value = bReference

        Dim sText As String
        sText = oJobService.execute(args)
        Dim oPreview As Object
        oPreview = oDialog.getControl("txt_preview")
        oPreview.setText(sText)
    End If
End Sub

Sub PerformInsertion()
    On Error GoTo ErrInsert
    If IsNull(oJobService) Then
        oJobService = CreateUnoService("org.quran.libreoffice.Job")
    End If
    If IsNull(oJobService) Then
        MsgBox "خدمة القرآن غير متوفرة (org.quran.libreoffice.Job)", 16, "خطأ"
        Exit Sub
    End If

    Dim args(10) As Object
    Dim i As Integer
    For i = 0 To 10
        args(i) = CreateUnoStruct("com.sun.star.beans.NamedValue")
    Next i
    args(0).Name = "action"
    args(0).Value = "insert"
    args(1).Name = "sura_no"
    args(1).Value = g_sura_no
    args(2).Name = "from_ayah"
    args(2).Value = g_from_ayah
    args(3).Name = "to_ayah"
    args(3).Value = g_to_ayah
    args(4).Name = "font_size"
    args(4).Value = g_font_size
    args(5).Name = "basmalah"
    args(5).Value = g_basmalah
    args(6).Name = "header"
    args(6).Value = g_header
    args(7).Name = "newline"
    args(7).Value = g_newline
    args(8).Name = "brackets"
    args(8).Value = g_brackets
    args(9).Name = "qala"
    args(9).Value = g_qala
    args(10).Name = "reference"
    args(10).Value = g_reference

    oJobService.execute(args)
    Exit Sub

ErrInsert:
    MsgBox "خطأ في الإدراج: " & Error$, 16, "خطأ"
End Sub

Sub ShowAbout()
    If IsNull(oJobService) Then
        oJobService = CreateUnoService("org.quran.libreoffice.Job")
    End If
    If Not IsNull(oJobService) Then
        Dim args(0) As Object
        args(0) = CreateUnoStruct("com.sun.star.beans.NamedValue")
        args(0).Name = "action"
        args(0).Value = "about"
        oJobService.execute(args)
    End If
End Sub

Sub PopulateSurahNames(ByRef aNames() As String)
    aNames(0) = "001 - سورة الفَاتِحة (7 آية)"
    aNames(1) = "002 - سورة البَقَرَة (286 آية)"
    aNames(2) = "003 - سورة آل عِمران (200 آية)"
    aNames(3) = "004 - سورة النِّسَاء (176 آية)"
    aNames(4) = "005 - سورة المَائدة (120 آية)"
    aNames(5) = "006 - سورة الأنعَام (165 آية)"
    aNames(6) = "007 - سورة الأعرَاف (206 آية)"
    aNames(7) = "008 - سورة الأنفَال (75 آية)"
    aNames(8) = "009 - سورة التوبَة (129 آية)"
    aNames(9) = "010 - سورة يُونس (109 آية)"
    aNames(10) = "011 - سورة هُود (123 آية)"
    aNames(11) = "012 - سورة يُوسُف (111 آية)"
    aNames(12) = "013 - سورة الرَّعد (43 آية)"
    aNames(13) = "014 - سورة إبراهِيم (52 آية)"
    aNames(14) = "015 - سورة الحِجر (99 آية)"
    aNames(15) = "016 - سورة النَّحل (128 آية)"
    aNames(16) = "017 - سورة الإسرَاء (111 آية)"
    aNames(17) = "018 - سورة الكَهف (110 آية)"
    aNames(18) = "019 - سورة مَريَم (98 آية)"
    aNames(19) = "020 - سورة طه (135 آية)"
    aNames(20) = "021 - سورة الأنبيَاء (112 آية)"
    aNames(21) = "022 - سورة الحج (78 آية)"
    aNames(22) = "023 - سورة المؤمنُون (118 آية)"
    aNames(23) = "024 - سورة النور (64 آية)"
    aNames(24) = "025 - سورة الفُرقَان (77 آية)"
    aNames(25) = "026 - سورة الشعراء (227 آية)"
    aNames(26) = "027 - سورة النَّمل (93 آية)"
    aNames(27) = "028 - سورة القَصَص (88 آية)"
    aNames(28) = "029 - سورة العَنكبُوت (69 آية)"
    aNames(29) = "030 - سورة الرُّوم (60 آية)"
    aNames(30) = "031 - سورة لُقمَان (34 آية)"
    aNames(31) = "032 - سورة السَّجدة (30 آية)"
    aNames(32) = "033 - سورة الأحزَاب (73 آية)"
    aNames(33) = "034 - سورة سَبإ (54 آية)"
    aNames(34) = "035 - سورة فَاطِر (45 آية)"
    aNames(35) = "036 - سورة يسٓ (83 آية)"
    aNames(36) = "037 - سورة الصَّافَات (182 آية)"
    aNames(37) = "038 - سورة صٓ (88 آية)"
    aNames(38) = "039 - سورة الزُّمَر (75 آية)"
    aNames(39) = "040 - سورة غَافِر (85 آية)"
    aNames(40) = "041 - سورة فُصِّلَت (54 آية)"
    aNames(41) = "042 - سورة الشُّوري (53 آية)"
    aNames(42) = "043 - سورة الزُّخرُف (89 آية)"
    aNames(43) = "044 - سورة الدُّخان (59 آية)"
    aNames(44) = "045 - سورة الجاثِية (37 آية)"
    aNames(45) = "046 - سورة الأحقَاف (35 آية)"
    aNames(46) = "047 - سورة مُحمد (38 آية)"
    aNames(47) = "048 - سورة الفَتح (29 آية)"
    aNames(48) = "049 - سورة الحُجُرَات (18 آية)"
    aNames(49) = "050 - سورة قٓ (45 آية)"
    aNames(50) = "051 - سورة الذَّاريَات (60 آية)"
    aNames(51) = "052 - سورة الطُّور (49 آية)"
    aNames(52) = "053 - سورة النَّجم (62 آية)"
    aNames(53) = "054 - سورة القَمَر (55 آية)"
    aNames(54) = "055 - سورة الرَّحمٰن (78 آية)"
    aNames(55) = "056 - سورة الوَاقِعة (96 آية)"
    aNames(56) = "057 - سورة الحدِيد (29 آية)"
    aNames(57) = "058 - سورة المُجَادلة (22 آية)"
    aNames(58) = "059 - سورة الحَشر (24 آية)"
    aNames(59) = "060 - سورة المُمتَحنَة (13 آية)"
    aNames(60) = "061 - سورة الصَّف (14 آية)"
    aNames(61) = "062 - سورة الجُمعَة (11 آية)"
    aNames(62) = "063 - سورة المُنَافِقُونَ (11 آية)"
    aNames(63) = "064 - سورة التغَابُن (18 آية)"
    aNames(64) = "065 - سورة الطَّلَاق (12 آية)"
    aNames(65) = "066 - سورة التَّحرِيم (12 آية)"
    aNames(66) = "067 - سورة المُلك (30 آية)"
    aNames(67) = "068 - سورة القَلَم (52 آية)"
    aNames(68) = "069 - سورة الحَاقة (52 آية)"
    aNames(69) = "070 - سورة المَعَارج (44 آية)"
    aNames(70) = "071 - سورة نُوح (28 آية)"
    aNames(71) = "072 - سورة الجِن (28 آية)"
    aNames(72) = "073 - سورة المُزمل (20 آية)"
    aNames(73) = "074 - سورة المُدثر (56 آية)"
    aNames(74) = "075 - سورة القِيَامة (40 آية)"
    aNames(75) = "076 - سورة الإنسَان (31 آية)"
    aNames(76) = "077 - سورة المُرسَلات (50 آية)"
    aNames(77) = "078 - سورة النَّبَإ (40 آية)"
    aNames(78) = "079 - سورة النَّازعَات (46 آية)"
    aNames(79) = "080 - سورة عَبَسَ (42 آية)"
    aNames(80) = "081 - سورة التَّكوير (29 آية)"
    aNames(81) = "082 - سورة الانفِطَار (19 آية)"
    aNames(82) = "083 - سورة المُطَففين (36 آية)"
    aNames(83) = "084 - سورة الانشِقَاق (25 آية)"
    aNames(84) = "085 - سورة البُرُوج (22 آية)"
    aNames(85) = "086 - سورة الطَّارق (17 آية)"
    aNames(86) = "087 - سورة الأعلى (19 آية)"
    aNames(87) = "088 - سورة الغَاشِية (26 آية)"
    aNames(88) = "089 - سورة الفَجر (30 آية)"
    aNames(89) = "090 - سورة البَلَد (20 آية)"
    aNames(90) = "091 - سورة الشَّمس (15 آية)"
    aNames(91) = "092 - سورة اللَّيل (21 آية)"
    aNames(92) = "093 - سورة الضُّحى (11 آية)"
    aNames(93) = "094 - سورة الشَّرح (8 آية)"
    aNames(94) = "095 - سورة التِّين (8 آية)"
    aNames(95) = "096 - سورة العَلَق (19 آية)"
    aNames(96) = "097 - سورة القَدر (5 آية)"
    aNames(97) = "098 - سورة البَينَة (8 آية)"
    aNames(98) = "099 - سورة الزَّلزَلة (8 آية)"
    aNames(99) = "100 - سورة العَاديَات (11 آية)"
    aNames(100) = "101 - سورة القَارعَة (11 آية)"
    aNames(101) = "102 - سورة التَّكاثُر (8 آية)"
    aNames(102) = "103 - سورة العَصر (3 آية)"
    aNames(103) = "104 - سورة الهُمَزة (9 آية)"
    aNames(104) = "105 - سورة الفِيل (5 آية)"
    aNames(105) = "106 - سورة قُرَيش (4 آية)"
    aNames(106) = "107 - سورة المَاعُون (7 آية)"
    aNames(107) = "108 - سورة الكَوثر (3 آية)"
    aNames(108) = "109 - سورة الكافِرون (6 آية)"
    aNames(109) = "110 - سورة النَّصر (3 آية)"
    aNames(110) = "111 - سورة المَسَد (5 آية)"
    aNames(111) = "112 - سورة الإخلَاص (4 آية)"
    aNames(112) = "113 - سورة الفَلَق (5 آية)"
    aNames(113) = "114 - سورة النَّاس (6 آية)"
End Sub

Sub InitSurahCounts()
    aSurahCounts(1) = 7
    aSurahCounts(2) = 286
    aSurahCounts(3) = 200
    aSurahCounts(4) = 176
    aSurahCounts(5) = 120
    aSurahCounts(6) = 165
    aSurahCounts(7) = 206
    aSurahCounts(8) = 75
    aSurahCounts(9) = 129
    aSurahCounts(10) = 109
    aSurahCounts(11) = 123
    aSurahCounts(12) = 111
    aSurahCounts(13) = 43
    aSurahCounts(14) = 52
    aSurahCounts(15) = 99
    aSurahCounts(16) = 128
    aSurahCounts(17) = 111
    aSurahCounts(18) = 110
    aSurahCounts(19) = 98
    aSurahCounts(20) = 135
    aSurahCounts(21) = 112
    aSurahCounts(22) = 78
    aSurahCounts(23) = 118
    aSurahCounts(24) = 64
    aSurahCounts(25) = 77
    aSurahCounts(26) = 227
    aSurahCounts(27) = 93
    aSurahCounts(28) = 88
    aSurahCounts(29) = 69
    aSurahCounts(30) = 60
    aSurahCounts(31) = 34
    aSurahCounts(32) = 30
    aSurahCounts(33) = 73
    aSurahCounts(34) = 54
    aSurahCounts(35) = 45
    aSurahCounts(36) = 83
    aSurahCounts(37) = 182
    aSurahCounts(38) = 88
    aSurahCounts(39) = 75
    aSurahCounts(40) = 85
    aSurahCounts(41) = 54
    aSurahCounts(42) = 53
    aSurahCounts(43) = 89
    aSurahCounts(44) = 59
    aSurahCounts(45) = 37
    aSurahCounts(46) = 35
    aSurahCounts(47) = 38
    aSurahCounts(48) = 29
    aSurahCounts(49) = 18
    aSurahCounts(50) = 45
    aSurahCounts(51) = 60
    aSurahCounts(52) = 49
    aSurahCounts(53) = 62
    aSurahCounts(54) = 55
    aSurahCounts(55) = 78
    aSurahCounts(56) = 96
    aSurahCounts(57) = 29
    aSurahCounts(58) = 22
    aSurahCounts(59) = 24
    aSurahCounts(60) = 13
    aSurahCounts(61) = 14
    aSurahCounts(62) = 11
    aSurahCounts(63) = 11
    aSurahCounts(64) = 18
    aSurahCounts(65) = 12
    aSurahCounts(66) = 12
    aSurahCounts(67) = 30
    aSurahCounts(68) = 52
    aSurahCounts(69) = 52
    aSurahCounts(70) = 44
    aSurahCounts(71) = 28
    aSurahCounts(72) = 28
    aSurahCounts(73) = 20
    aSurahCounts(74) = 56
    aSurahCounts(75) = 40
    aSurahCounts(76) = 31
    aSurahCounts(77) = 50
    aSurahCounts(78) = 40
    aSurahCounts(79) = 46
    aSurahCounts(80) = 42
    aSurahCounts(81) = 29
    aSurahCounts(82) = 19
    aSurahCounts(83) = 36
    aSurahCounts(84) = 25
    aSurahCounts(85) = 22
    aSurahCounts(86) = 17
    aSurahCounts(87) = 19
    aSurahCounts(88) = 26
    aSurahCounts(89) = 30
    aSurahCounts(90) = 20
    aSurahCounts(91) = 15
    aSurahCounts(92) = 21
    aSurahCounts(93) = 11
    aSurahCounts(94) = 8
    aSurahCounts(95) = 8
    aSurahCounts(96) = 19
    aSurahCounts(97) = 5
    aSurahCounts(98) = 8
    aSurahCounts(99) = 8
    aSurahCounts(100) = 11
    aSurahCounts(101) = 11
    aSurahCounts(102) = 8
    aSurahCounts(103) = 3
    aSurahCounts(104) = 9
    aSurahCounts(105) = 5
    aSurahCounts(106) = 4
    aSurahCounts(107) = 7
    aSurahCounts(108) = 3
    aSurahCounts(109) = 6
    aSurahCounts(110) = 3
    aSurahCounts(111) = 5
    aSurahCounts(112) = 4
    aSurahCounts(113) = 5
    aSurahCounts(114) = 6
End Sub
'''

# Escape for XML
escaped = basic_source.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

xba_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE script:module PUBLIC "-//OpenOffice.org//DTD OfficeDocument 1.0//EN" "module.dtd">
<script:module xmlns:script="http://openoffice.org/2000/script" script:name="QuranModule" script:language="StarBasic">{escaped}</script:module>
'''

xba_path = os.path.join(EXT_DIR, "QuranBasic", "QuranModule.xba")
with open(xba_path, "w", encoding="utf-8") as f:
    f.write(xba_content)
print(f"Written: {xba_path}")

# 3. Bump version in description.xml to 3.9.2
desc_path = os.path.join(EXT_DIR, "description.xml")
with open(desc_path, "r", encoding="utf-8") as f:
    desc_content = f.read()

new_desc = re.sub(r'<version\s+value="[^"]*"', '<version value="3.9.2"', desc_content)
with open(desc_path, "w", encoding="utf-8") as f:
    f.write(new_desc)
print("Updated description.xml version to 3.9.2")

# 4. Build .oxt
oxt_path = os.path.join(BASE_DIR, "quran_libreoffice.oxt")
if os.path.exists(oxt_path):
    os.remove(oxt_path)

with zipfile.ZipFile(oxt_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(EXT_DIR):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, EXT_DIR)
            zf.write(full_path, rel_path)

print(f"Successfully generated {oxt_path} ({os.path.getsize(oxt_path)} bytes)")
