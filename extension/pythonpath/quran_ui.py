# -*- coding: utf-8 -*-
"""
Quran UI Dialog and Writer Insertion Engine for LibreOffice
Uses native DialogProvider with QuranDialog.xdl
"""

try:
    import uno
    import unohelper
    from com.sun.star.awt import (
        XActionListener,
        XItemListener,
        XTextListener
    )
except ImportError:
    uno = None
    class _MockBase:
        pass
    class _MockUnoHelper:
        Base = _MockBase
    unohelper = _MockUnoHelper()
    XActionListener = object
    XItemListener = object
    XTextListener = object

import os
from quran_db import QuranDB, BASMALAH, normalize_arabic

DEFAULT_FONT = "KFGQPC_HAFS_Uthmanic_Script_H"


import tempfile
DEBUG_LOG = os.path.join(tempfile.gettempdir(), "quran_libreoffice_debug.log")

def log_debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except:
        pass


class ButtonClickListener(unohelper.Base, XActionListener):
    def __init__(self, callback):
        self.callback = callback

    def actionPerformed(self, action_event):
        self.callback(action_event)

    def disposing(self, source):
        pass


class ItemChangeListener(unohelper.Base, XItemListener):
    def __init__(self, callback):
        self.callback = callback

    def itemStateChanged(self, item_event):
        self.callback(item_event)

    def disposing(self, source):
        pass


class QuranDialogRunner:
    def __init__(self, ctx, frame=None):
        self.ctx = ctx
        self.frame = frame
        self.smgr = ctx.getServiceManager()
        self.db = QuranDB()
        self.surahs = self.db.get_all_surahs()
        self.current_surah_idx = 0  # 0-indexed (Surah 1: Al-Fatiha)
        self.search_results = []
        self.dialog = None

    def get_current_payload(self, is_preview=False):
        surah = self.surahs[self.current_surah_idx]
        num_from = self.dialog.getControl("num_from")
        num_to = self.dialog.getControl("num_to")
        chk_basmalah = self.dialog.getControl("chk_basmalah")
        chk_header = self.dialog.getControl("chk_header")
        chk_newline = self.dialog.getControl("chk_newline")
        chk_brackets = self.dialog.getControl("chk_brackets")

        f_aya = int(num_from.getValue()) if num_from else 1
        t_aya = int(num_to.getValue()) if num_to else 7
        if f_aya > t_aya:
            t_aya = f_aya

        b_basmalah = (chk_basmalah.getState() == 1) if chk_basmalah else True
        b_header = (chk_header.getState() == 1) if chk_header else True
        b_newline = (chk_newline.getState() == 1) if chk_newline else False
        b_brackets = (chk_brackets.getState() == 1) if chk_brackets else True

        return self.db.build_quran_payload(
            sura_no=surah["sura_no"],
            from_ayah=f_aya,
            to_ayah=t_aya,
            include_basmalah=b_basmalah,
            include_header=b_header,
            line_per_ayah=b_newline,
            include_brackets=b_brackets,
            is_preview=is_preview
        )

    def on_surah_selected(self, event):
        lst_surah = self.dialog.getControl("lst_surah")
        pos = lst_surah.getSelectedItemPos()
        if pos < 0 or pos >= len(self.surahs):
            return
        self.current_surah_idx = pos
        surah = self.surahs[pos]
        max_ayah = float(surah["ayah_count"])

        num_from = self.dialog.getControl("num_from")
        num_to = self.dialog.getControl("num_to")
        if num_from and num_to:
            num_from.getModel().setPropertyValue("ValueMax", max_ayah)
            num_to.getModel().setPropertyValue("ValueMax", max_ayah)
            num_from.setValue(1.0)
            default_to = min(max_ayah, 5.0)
            num_to.setValue(default_to)

        chk_basmalah = self.dialog.getControl("chk_basmalah")
        if chk_basmalah:
            if surah["sura_no"] == 9:
                chk_basmalah.setState(0)
            else:
                chk_basmalah.setState(1)

        self.update_preview()

    def on_search_clicked(self, event):
        txt_search = self.dialog.getControl("txt_search")
        if not txt_search:
            return
        query = txt_search.getText().strip()
        if not query:
            return

        results = self.db.search(query, limit=50)
        self.search_results = results

        lst_search = self.dialog.getControl("lst_search")
        if not lst_search:
            return

        lst_search.removeItems(0, lst_search.getItemCount())

        if not results:
            lst_search.addItems(("لم يتم العثور على نتائج مطابقة",), 0)
            return

        items = []
        for r in results:
            snippet = r["aya_text_emlaey"][:35].replace("\n", " ")
            items.append(f"سورة {r['sura_name_ar']} [آية {r['aya_no']}] [{r['sura_no']:03d}:{r['aya_no']:03d}] - {snippet}...")
        lst_search.addItems(tuple(items), 0)

    def on_search_result_selected(self, event):
        lst_search = self.dialog.getControl("lst_search")
        pos = lst_search.getSelectedItemPos()
        if pos < 0 or pos >= len(self.search_results):
            return

        res = self.search_results[pos]
        target_sura = res["sura_no"]
        target_aya = res["aya_no"]

        target_idx = target_sura - 1
        if 0 <= target_idx < len(self.surahs):
            self.current_surah_idx = target_idx
            lst_surah = self.dialog.getControl("lst_surah")
            if lst_surah:
                lst_surah.selectItemPos(target_idx, True)

            max_ayah = float(self.surahs[target_idx]["ayah_count"])
            num_from = self.dialog.getControl("num_from")
            num_to = self.dialog.getControl("num_to")
            if num_from and num_to:
                num_from.getModel().setPropertyValue("ValueMax", max_ayah)
                num_to.getModel().setPropertyValue("ValueMax", max_ayah)
                num_from.setValue(float(target_aya))
                num_to.setValue(float(target_aya))

            self.update_preview()

    def update_preview(self, event=None):
        try:
            payload = self.get_current_payload(is_preview=True)
            txt_preview = self.dialog.getControl("txt_preview")
            if txt_preview and payload:
                preview_text = payload.get("combined_text", "")
                txt_preview.setText(preview_text)
        except Exception as e:
            log_debug(f"Error in update_preview: {e}")

    def on_insert_clicked(self, event):
        try:
            payload = self.get_current_payload(is_preview=False)
            if not payload:
                self.show_message("تنبيه", "تعذر تجهيز النص القرآني للإدراج.")
                return

            num_size = self.dialog.getControl("num_font_size")
            font_size = float(num_size.getValue()) if num_size else 20.0

            success = self.insert_into_writer(payload, font_size)
            if success:
                self.dialog.endExecute()
        except Exception as e:
            import traceback
            log_debug(f"Error in on_insert_clicked: {traceback.format_exc()}")
            self.show_message("خطأ في الإدراج", str(e))

    def insert_into_writer(self, payload, font_size=20.0, font_name="kfgqpc_hafs_uthmanic _script"):
        desktop = self.smgr.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
        doc = desktop.getCurrentComponent()

        if not doc or not hasattr(doc, "getText"):
            self.show_message("تنبيه", "يرجى فتح مستند نصي في محرر النصوص (LibreOffice Writer) قبل الإدراج.")
            return False

        text = doc.getText()
        controller = doc.getCurrentController()
        view_cursor = controller.getViewCursor()
        cursor = text.createTextCursorByRange(view_cursor.getStart())

        is_locked = False
        try:
            if hasattr(doc, "lockControllers"):
                try:
                    doc.lockControllers()
                    is_locked = True
                except:
                    pass
            if hasattr(doc, "addActionLock"):
                try:
                    doc.addActionLock()
                except:
                    pass

        # 1. Header if present
        if payload.get("header"):
            try:
                cursor.setPropertyValue("WritingMode", 1)  # RTL
            except:
                pass
            try:
                from com.sun.star.style.ParagraphAdjust import CENTER
                cursor.setPropertyValue("ParaAdjust", CENTER)
            except:
                pass
            cursor.setPropertyValue("CharFontNameComplex", "Traditional Arabic")
            cursor.setPropertyValue("CharFontName", "Traditional Arabic")
            cursor.setPropertyValue("CharHeightComplex", float(font_size - 2.0))
            cursor.setPropertyValue("CharHeight", float(font_size - 2.0))
            cursor.setPropertyValue("CharWeightComplex", 100.0)
            cursor.setPropertyValue("CharWeight", 100.0)
            text.insertString(cursor, payload["header"] + "\n", False)

        # 2. Basmalah if present
        if payload.get("basmalah"):
            try:
                cursor.setPropertyValue("WritingMode", 1)  # RTL
            except:
                pass
            try:
                from com.sun.star.style.ParagraphAdjust import CENTER
                cursor.setPropertyValue("ParaAdjust", CENTER)
            except:
                pass
            cursor.setPropertyValue("CharFontNameComplex", font_name)
            cursor.setPropertyValue("CharFontName", font_name)
            cursor.setPropertyValue("CharHeightComplex", float(font_size))
            cursor.setPropertyValue("CharHeight", float(font_size))
            cursor.setPropertyValue("CharWeightComplex", 100.0)
            cursor.setPropertyValue("CharWeight", 100.0)
            text.insertString(cursor, payload["basmalah"] + "\n", False)

        # 3. Main Verse Quote Line (Align Start in RTL, without kashida stretching)
        try:
            cursor.setPropertyValue("WritingMode", 1)  # RTL
            from com.sun.star.style.ParagraphAdjust import START
            cursor.setPropertyValue("ParaAdjust", START)
        except:
            try:
                from com.sun.star.style.ParagraphAdjust import RIGHT
                cursor.setPropertyValue("ParaAdjust", RIGHT)
            except:
                pass

        # a) Qala Taala prefix (Traditional Arabic regular, NOT bold)
        if payload.get("qala_taala"):
            cursor.setPropertyValue("CharFontNameComplex", "Traditional Arabic")
            cursor.setPropertyValue("CharFontName", "Traditional Arabic")
            cursor.setPropertyValue("CharHeightComplex", float(font_size))
            cursor.setPropertyValue("CharHeight", float(font_size))
            cursor.setPropertyValue("CharWeightComplex", 100.0)
            cursor.setPropertyValue("CharWeight", 100.0)
            text.insertString(cursor, payload["qala_taala"] + " ", False)

        # b) Verses with Uthmanic Font and Ornate Brackets
        cursor.setPropertyValue("CharFontNameComplex", font_name)
        cursor.setPropertyValue("CharFontName", font_name)
        cursor.setPropertyValue("CharHeightComplex", float(font_size))
        cursor.setPropertyValue("CharHeight", float(font_size))
        cursor.setPropertyValue("CharWeightComplex", 100.0)
        cursor.setPropertyValue("CharWeight", 100.0)
        body_to_insert = payload.get("body_text")
        if not body_to_insert:
            sep = "\n" if payload.get("line_per_ayah") else " "
            body_to_insert = sep.join(payload["verses"])
        text.insertString(cursor, body_to_insert, False)

        # c) Reference citation [الفَاتِحة: 1-4] (Traditional Arabic regular, NOT bold)
        if payload.get("reference"):
            cursor.setPropertyValue("CharFontNameComplex", "Traditional Arabic")
            cursor.setPropertyValue("CharFontName", "Traditional Arabic")
            cursor.setPropertyValue("CharHeightComplex", float(font_size - 2.0))
            cursor.setPropertyValue("CharHeight", float(font_size - 2.0))
            cursor.setPropertyValue("CharWeightComplex", 100.0)
            cursor.setPropertyValue("CharWeight", 100.0)
            text.insertString(cursor, " " + payload["reference"], False)

            text.insertString(cursor, "\n", False)

            # Move view cursor to end of insertion
            view_cursor.gotoRange(cursor.getEnd(), False)
            return True
        finally:
            if hasattr(doc, "removeActionLock"):
                try:
                    doc.removeActionLock()
                except:
                    pass
            if is_locked and hasattr(doc, "unlockControllers"):
                try:
                    doc.unlockControllers()
                except:
                    pass

    def show_message(self, title, message):
        try:
            toolkit = self.smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
            from com.sun.star.awt.MessageBoxType import MESSAGEBOX
            from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK
            msgbox = toolkit.createMessageBox(None, MESSAGEBOX, BUTTONS_OK, title, message)
            msgbox.execute()
        except Exception as e:
            log_debug(f"show_message error: {e}")

    def show(self):
        log_debug("QuranDialogRunner.show() called")
        try:
            # 1. Ensure QuranBasic library is loaded in ApplicationDialogLibraryContainer
            try:
                dlg_cont = self.smgr.createInstanceWithContext("com.sun.star.script.ApplicationDialogLibraryContainer", self.ctx)
                if dlg_cont and dlg_cont.hasByName("QuranBasic"):
                    if not dlg_cont.isLibraryLoaded("QuranBasic"):
                        dlg_cont.loadLibrary("QuranBasic")
                        log_debug("Loaded QuranBasic dialog library successfully")
                    else:
                        log_debug("QuranBasic dialog library was already loaded")
                else:
                    names = dlg_cont.getElementNames() if dlg_cont else 'None'
                    log_debug(f"QuranBasic not found in ApplicationDialogLibraryContainer. Available: {names}")
            except Exception as e:
                log_debug(f"Warning checking ApplicationDialogLibraryContainer: {e}")

            # 2. Create Dialog via DialogProvider
            dp = self.smgr.createInstanceWithContext("com.sun.star.awt.DialogProvider", self.ctx)
            log_debug(f"DialogProvider instance: {dp}")

            candidate_urls = [
                "vnd.sun.star.script:QuranBasic.QuranDialog?location=application",
                "vnd.sun.star.script:QuranBasic.QuranDialog?location=user",
                "vnd.sun.star.script:QuranBasic.QuranDialog?location=share",
            ]

            self.dialog = None
            for url in candidate_urls:
                try:
                    log_debug(f"Attempting to create dialog with URL: {url}")
                    self.dialog = dp.createDialog(url)
                    if self.dialog:
                        log_debug(f"SUCCESS creating dialog with URL: {url}")
                        break
                except Exception as e:
                    log_debug(f"Failed URL {url}: {e}")

            if not self.dialog:
                # Fallback: file URL of QuranDialog.xdl
                xdl_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "QuranBasic", "QuranDialog.xdl")
                file_url = "file:///" + xdl_path.replace("\\", "/")
                log_debug(f"Attempting fallback file URL: {file_url}")
                try:
                    self.dialog = dp.createDialog(file_url)
                    if self.dialog:
                        log_debug(f"SUCCESS creating dialog with fallback file URL: {file_url}")
                except Exception as e:
                    log_debug(f"Fallback file URL failed: {e}")

            if not self.dialog:
                err_msg = "تعذر إنشاء نافذة القرآن الكريم عبر DialogProvider. يرجى مراجعة debug.log."
                log_debug(err_msg)
                self.show_message("خطأ في الواجهة", err_msg)
                return

            # 2.5 Apply RTL WritingMode across dialog and all controls
            try:
                if hasattr(self.dialog.getModel(), "WritingMode"):
                    self.dialog.getModel().setPropertyValue("WritingMode", 1)
                for name in self.dialog.getModel().getElementNames():
                    m = self.dialog.getModel().getByName(name)
                    if hasattr(m, "WritingMode") or (hasattr(m, "hasPropertyByName") and m.hasPropertyByName("WritingMode")):
                        try:
                            m.setPropertyValue("WritingMode", 1)
                        except Exception:
                            pass
            except Exception as e:
                log_debug(f"WritingMode setup warning: {e}")

            # 3. Populate Surahs in lst_surah
            lst_surah = self.dialog.getControl("lst_surah")
            log_debug(f"lst_surah control: {lst_surah}")
            if lst_surah:
                surah_titles = tuple(
                    f"سورة {s['sura_name_ar']} [{s['sura_no']:03d}] ({s['ayah_count']} آية)"
                    for s in self.surahs
                )
                lst_surah.addItems(surah_titles, 0)
                lst_surah.selectItemPos(0, True)

            # 4. Set default values for num_from and num_to
            num_from = self.dialog.getControl("num_from")
            num_to = self.dialog.getControl("num_to")
            if num_from and num_to:
                num_from.getModel().setPropertyValue("ValueMax", 7.0)
                num_to.getModel().setPropertyValue("ValueMax", 7.0)
                num_from.setValue(1.0)
                num_to.setValue(7.0)

            # 5. Attach event listeners
            if lst_surah:
                lst_surah.addItemListener(ItemChangeListener(self.on_surah_selected))

            btn_search = self.dialog.getControl("btn_search")
            if btn_search:
                btn_search.addActionListener(ButtonClickListener(self.on_search_clicked))

            lst_search = self.dialog.getControl("lst_search")
            if lst_search:
                lst_search.addItemListener(ItemChangeListener(self.on_search_result_selected))

            btn_insert = self.dialog.getControl("btn_insert")
            if btn_insert:
                btn_insert.addActionListener(ButtonClickListener(self.on_insert_clicked))

            chk_basmalah = self.dialog.getControl("chk_basmalah")
            chk_header = self.dialog.getControl("chk_header")
            chk_newline = self.dialog.getControl("chk_newline")
            if chk_basmalah:
                chk_basmalah.addItemListener(ItemChangeListener(self.update_preview))
            if chk_header:
                chk_header.addItemListener(ItemChangeListener(self.update_preview))
            if chk_newline:
                chk_newline.addItemListener(ItemChangeListener(self.update_preview))

            # Initial preview
            self.update_preview()

            # 6. Show modal dialog
            log_debug("Calling self.dialog.execute()...")
            self.dialog.execute()
            log_debug("dialog.execute() closed, disposing...")
            self.dialog.dispose()
            log_debug("Dialog disposed successfully.")

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log_debug(f"Exception in QuranDialogRunner.show: {tb}")
            self.show_message("خطأ في تشغيل نافذة القرآن", f"{e}\n\n{tb[:300]}")


def show_quran_dialog(ctx, frame=None):
    runner = QuranDialogRunner(ctx, frame)
    runner.show()
