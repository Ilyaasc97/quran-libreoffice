# -*- coding: utf-8 -*-
"""
Quran Extension for LibreOffice
Main UNO Component & Backend Service Provider
"""

import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
pythonpath_dir = os.path.join(current_dir, "pythonpath")
if pythonpath_dir not in sys.path:
    sys.path.insert(0, pythonpath_dir)

try:
    import uno
    import unohelper
    from com.sun.star.task import XJob, XJobExecutor
    from com.sun.star.frame import XDispatchProvider, XDispatch, FeatureStateEvent
    from com.sun.star.lang import XServiceInfo, XInitialization
except ImportError:
    uno = None
    class _MockBase:
        pass
    class _MockUnoHelper:
        Base = _MockBase
        ImplementationHelper = None
    unohelper = _MockUnoHelper()
    XJob = object
    XJobExecutor = object
    XDispatchProvider = object
    XDispatch = object
    XServiceInfo = object
    XInitialization = object
    FeatureStateEvent = None

from quran_db import QuranDB
import tempfile

DEBUG_LOG = os.path.join(tempfile.gettempdir(), "quran_libreoffice_debug.log")

def log_debug(msg):
    try:
        with open(DEBUG_LOG, "a", encoding="utf-8") as f:
            f.write(str(msg) + "\n")
    except:
        pass

log_debug("=== quran_extension.py loaded ===")

DEFAULT_FONT = "KFGQPC_HAFS_Uthmanic_Script_H"
JOB_IMPLEMENTATION_NAME = "org.quran.libreoffice.Job"
PROTOCOL_IMPLEMENTATION_NAME = "org.quran.libreoffice.ProtocolHandler"
PROTOCOL = "org.quran.libreoffice:"


class QuranJob(unohelper.Base, XJob, XJobExecutor, XServiceInfo):
    def __init__(self, ctx):
        self.ctx = ctx
        log_debug("QuranJob initialized")

    def trigger(self, event):
        log_debug(f"QuranJob.trigger called with event='{event}'")
        try:
            if "About" in event or "about" in event:
                self.show_about_box()
            else:
                show_quran_dialog(self.ctx)
        except Exception as e:
            import traceback
            log_debug(f"Error in QuranJob.trigger: {traceback.format_exc()}")
            self.show_message("خطأ في تشغيل إضافة القرآن", str(e))

    def execute(self, args):
        log_debug(f"QuranJob.execute called with {len(args) if args else 0} args")
        params = {}
        raw_command = ""
        if args:
            for arg in args:
                if hasattr(arg, "Name") and hasattr(arg, "Value"):
                    params[arg.Name] = arg.Value
                    # service:org.quran.libreoffice.Job?InsertQuran sends
                    # EnvType="DISPATCH", JobConfig contains the command
                    if arg.Name in ("Command", "JobConfig", "EnvType"):
                        raw_command = str(arg.Value)
                    log_debug(f"  arg: Name='{arg.Name}' Value='{arg.Value}'")

        # Determine action: either from explicit "action" param or from command/URL
        action = params.get("action", "")
        if not action:
            # service: URL invocation - command in raw_command or all params
            combined = raw_command + " ".join(str(v) for v in params.values())
            log_debug(f"No explicit action. combined='{combined}'")
            if "About" in combined or "about" in combined:
                action = "about"
            else:
                action = "show_dialog"

        log_debug(f"Final action: '{action}'")

        try:
            db = QuranDB()

            if action == "insert":
                sura_no = int(params.get("sura_no", 1))
                from_ayah = int(params.get("from_ayah", 1))
                to_ayah = int(params.get("to_ayah", 7))
                font_size = float(params.get("font_size", 20.0))
                basmalah = bool(params.get("basmalah", True))
                header = bool(params.get("header", False))
                newline = bool(params.get("newline", False))
                brackets = bool(params.get("brackets", True))
                qala = bool(params.get("qala", True))
                reference = bool(params.get("reference", True))

                payload = db.build_quran_payload(
                    sura_no=sura_no,
                    from_ayah=from_ayah,
                    to_ayah=to_ayah,
                    include_basmalah=basmalah,
                    include_header=header,
                    line_per_ayah=newline,
                    include_brackets=brackets,
                    include_qala=qala,
                    include_ref=reference
                )
                if payload:
                    success = self.insert_into_writer(payload, font_size)
                    return success
                return False

            elif action == "search":
                query = str(params.get("query", "")).strip()
                log_debug(f"Search query: {query}")
                results = db.search(query, limit=50)
                formatted = []
                for r in results:
                    snippet = r["aya_text_emlaey"][:40].replace("\n", " ")
                    line = f"{r['sura_no']:03d}:{r['aya_no']:03d} - سورة {r['sura_name_ar']} - {snippet}..."
                    formatted.append(line)
                log_debug(f"Found {len(formatted)} results")
                return tuple(formatted)

            elif action == "preview":
                sura_no = int(params.get("sura_no", 1))
                from_ayah = int(params.get("from_ayah", 1))
                to_ayah = int(params.get("to_ayah", 7))
                basmalah = bool(params.get("basmalah", True))
                header = bool(params.get("header", False))
                newline = bool(params.get("newline", False))
                brackets = bool(params.get("brackets", True))
                qala = bool(params.get("qala", True))
                reference = bool(params.get("reference", True))

                payload = db.build_quran_payload(
                    sura_no=sura_no,
                    from_ayah=from_ayah,
                    to_ayah=to_ayah,
                    include_basmalah=basmalah,
                    include_header=header,
                    line_per_ayah=newline,
                    include_brackets=brackets,
                    include_qala=qala,
                    include_ref=reference,
                    is_preview=True
                )
                return payload["combined_text"] if payload else ""

            elif "about" in action.lower():
                self.show_about_box()
                return ()

            elif action in ("show_dialog", "InsertQuran") or not action:
                # Default: show Quran insert dialog
                log_debug("Calling show_quran_dialog...")
                show_quran_dialog(self.ctx)
                return ()

            else:
                # Unknown action, still show dialog
                log_debug(f"Unknown action '{action}', showing dialog anyway")
                show_quran_dialog(self.ctx)
                return ()

        except Exception as e:
            import traceback
            tb = traceback.format_exc()
            log_debug(f"Error in QuranJob.execute: {tb}")
            self.show_message("خطأ في تشغيل إضافة القرآن", str(e))
            return ()

    def launch_basic_dialog(self):
        try:
            smgr = self.ctx.getServiceManager()
            msp = smgr.createInstanceWithContext(
                "com.sun.star.script.provider.MasterScriptProviderFactory", self.ctx
            ).createScriptProvider("")
            script = msp.getScript("vnd.sun.star.script:QuranBasic.QuranModule.InsertQuran?language=Basic&location=application")
            script.invoke((), (), ())
        except Exception as e:
            log_debug(f"Error launching basic dialog: {e}")

    def insert_into_writer(self, payload, font_size=20.0, font_name=DEFAULT_FONT):
        smgr = self.ctx.getServiceManager()
        desktop = smgr.createInstanceWithContext("com.sun.star.frame.Desktop", self.ctx)
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

    def show_about_box(self):
        msg = (
            "إضافة إدخال القرآن الكريم لبرنامج LibreOffice Writer\n"
            "الإصدار: 2.0\n\n"
            "• معتمدة على بيانات وخطوط مجمع الملك فهد لطباعة المصحف الشريف.\n"
            "• خط المصحف: kfgqpc_hafs_uthmanic _script\n"
            "• تدعم البحث اللحظي، واختيار السور، وإدراج البسملة وضبط التنسيق تلقائياً."
        )
        self.show_message("حول إضافة القرآن الكريم", msg)

    def show_message(self, title, message):
        try:
            smgr = self.ctx.getServiceManager()
            toolkit = smgr.createInstanceWithContext("com.sun.star.awt.Toolkit", self.ctx)
            from com.sun.star.awt.MessageBoxType import MESSAGEBOX
            from com.sun.star.awt.MessageBoxButtons import BUTTONS_OK
            msgbox = toolkit.createMessageBox(None, MESSAGEBOX, BUTTONS_OK, title, message)
            msgbox.execute()
        except Exception as e:
            log_debug(f"show_message error: {e}")

    def getImplementationName(self):
        return JOB_IMPLEMENTATION_NAME

    def supportsService(self, name):
        return name in self.getSupportedServiceNames()

    def getSupportedServiceNames(self):
        return (JOB_IMPLEMENTATION_NAME, "com.sun.star.task.Job", "com.sun.star.task.JobExecutor")


class QuranDispatch(unohelper.Base, XDispatch):
    def __init__(self, ctx, frame):
        self.ctx = ctx
        self.frame = frame

    def dispatch(self, url, args):
        cmd = url.Path if hasattr(url, 'Path') else str(url)
        log_debug(f"QuranDispatch.dispatch called with cmd='{cmd}' url='{url.Complete if hasattr(url, 'Complete') else url}'")
        try:
            if "About" in cmd or "about" in cmd:
                job = QuranJob(self.ctx)
                job.show_about_box()
            else:
                # Default: InsertQuran -> show Python dialog
                show_quran_dialog(self.ctx)
        except Exception as e:
            import traceback
            log_debug(f"Error in dispatch: {traceback.format_exc()}")

    def addStatusListener(self, listener, url):
        if FeatureStateEvent is not None:
            state = FeatureStateEvent()
            state.FeatureURL = url
            state.Source = self
            state.IsEnabled = True
            state.Requery = False
            state.State = None
            try:
                listener.statusChanged(state)
            except Exception as e:
                log_debug(f"Error in addStatusListener: {e}")

    def removeStatusListener(self, listener, url):
        pass


class QuranProtocolHandler(unohelper.Base, XDispatchProvider, XInitialization, XServiceInfo):
    def __init__(self, ctx):
        self.ctx = ctx
        self.frame = None

    def initialize(self, args):
        if args:
            self.frame = args[0]

    def queryDispatch(self, url, target_frame_name, search_flags):
        complete = url.Complete if hasattr(url, "Complete") else str(url)
        log_debug(f"queryDispatch called: complete='{complete}'")
        if "org.quran.libreoffice" in complete:
            log_debug("queryDispatch: MATCH! Returning QuranDispatch")
            return QuranDispatch(self.ctx, self.frame)
        return None

    def queryDispatches(self, requests):
        return tuple(
            self.queryDispatch(req.FeatureURL, req.FrameName, req.SearchFlags)
            for req in requests
        )

    def getImplementationName(self):
        return PROTOCOL_IMPLEMENTATION_NAME

    def supportsService(self, name):
        return name in self.getSupportedServiceNames()

    def getSupportedServiceNames(self):
        return ("com.sun.star.frame.ProtocolHandler", PROTOCOL_IMPLEMENTATION_NAME)


# Registration Helper for LibreOffice UNO
g_ImplementationHelper = unohelper.ImplementationHelper()

g_ImplementationHelper.addImplementation(
    QuranJob,
    JOB_IMPLEMENTATION_NAME,
    (JOB_IMPLEMENTATION_NAME, "com.sun.star.task.Job", "com.sun.star.task.JobExecutor"),
)

g_ImplementationHelper.addImplementation(
    QuranProtocolHandler,
    PROTOCOL_IMPLEMENTATION_NAME,
    ("com.sun.star.frame.ProtocolHandler",),
)
