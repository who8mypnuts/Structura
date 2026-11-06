// Golden dump harness for Structure Synth 1.5 (test-only; links LGPL/GPL legacy code).
//
// Usage: golden_dump MODE SCRIPT SEED OUT [TEMPLATE]
//   MODE = dump      -> OUT receives one JSON object per line for every renderer call
//          template  -> OUT receives the TemplateRenderer output for TEMPLATE
//          obj       -> OUT receives ObjRenderer output (sphere 10x10 divisions, no grouping)
// stdout receives a JSON "meta" object: logs, errors, builder results.

#include <QApplication>
#include <QDoubleSpinBox>
#include <QFile>
#include <QSpinBox>
#include <QTextStream>
#include <cstdio>

#include "StructureSynth/Model/Builder.h"
#include "StructureSynth/Model/RandomStreams.h"
#include "StructureSynth/Model/Rendering/ObjRenderer.h"
#include "StructureSynth/Model/Rendering/TemplateRenderer.h"
#include "StructureSynth/Parser/EisenParser.h"
#include "StructureSynth/Parser/Preprocessor.h"
#include "StructureSynth/Parser/Tokenizer.h"
#include "SyntopiaCore/Logging/Logging.h"

using namespace StructureSynth::Model;
using namespace StructureSynth::Model::Rendering;
using namespace StructureSynth::Parser;
using namespace SyntopiaCore::Math;
using namespace SyntopiaCore::Logging;
using SyntopiaCore::GLEngine::PrimitiveClass;

static QString num(double v) { return QString::number(v, 'g', 9); }
static QString vec(const Vector3f& v) { return "[" + num(v.x()) + "," + num(v.y()) + "," + num(v.z()) + "]"; }

static QString jstr(const QString& s) {
	QString o = "\"";
	for (QChar c : s) {
		if (c == '"' || c == '\\') { o += '\\'; o += c; }
		else if (c == '\n') o += "\\n";
		else if (c == '\r') o += "\\r";
		else if (c == '\t') o += "\\t";
		else if (c.unicode() < 0x20) o += QString("\\u%1").arg(c.unicode(), 4, 16, QChar('0'));
		else o += c;
	}
	return o + "\"";
}

class JsonLogger : public Logger {
public:
	QStringList lines;
	void log(QString message, LogLevel priority) override {
		lines.append(QString("{\"level\":%1,\"msg\":%2}").arg(int(priority)).arg(jstr(message)));
	}
};

class DumpRenderer : public Renderer {
public:
	QStringList out;
	Vector3f rgb, prevRgb;
	double alpha = 1, prevAlpha = 1;

	QString col() const { return QString(",\"rgb\":%1,\"a\":%2").arg(vec(rgb)).arg(num(alpha)); }
	static QString cls(PrimitiveClass* c) { return QString(",\"cls\":%1").arg(jstr(c ? c->name : "")); }
	void put(const QString& s) { out.append(s); }

	void drawBox(Vector3f b, Vector3f d1, Vector3f d2, Vector3f d3, PrimitiveClass* c) override {
		put(QString("{\"t\":\"box\",\"base\":%1,\"d1\":%2,\"d2\":%3,\"d3\":%4%5%6}")
			.arg(vec(b), vec(d1), vec(d2), vec(d3), col(), cls(c)));
	}
	void drawGrid(Vector3f b, Vector3f d1, Vector3f d2, Vector3f d3, PrimitiveClass* c) override {
		put(QString("{\"t\":\"grid\",\"base\":%1,\"d1\":%2,\"d2\":%3,\"d3\":%4%5%6}")
			.arg(vec(b), vec(d1), vec(d2), vec(d3), col(), cls(c)));
	}
	void drawMesh(Vector3f sb, Vector3f sd1, Vector3f sd2, Vector3f eb, Vector3f ed1, Vector3f ed2,
		PrimitiveClass* c) override {
		put(QString("{\"t\":\"mesh\",\"sb\":%1,\"sd1\":%2,\"sd2\":%3,\"eb\":%4,\"ed1\":%5,\"ed2\":%6%7"
			",\"prgb\":%8,\"pa\":%9%10}")
			.arg(vec(sb), vec(sd1), vec(sd2), vec(eb), vec(ed1), vec(ed2), col(), vec(prevRgb))
			.arg(num(prevAlpha)).arg(cls(c)));
	}
	void drawLine(Vector3f f, Vector3f t, PrimitiveClass* c) override {
		put(QString("{\"t\":\"line\",\"from\":%1,\"to\":%2%3%4}").arg(vec(f), vec(t), col(), cls(c)));
	}
	void drawDot(Vector3f p, PrimitiveClass* c) override {
		put(QString("{\"t\":\"dot\",\"pos\":%1%2%3}").arg(vec(p), col(), cls(c)));
	}
	void drawSphere(Vector3f ce, float r, PrimitiveClass* c) override {
		put(QString("{\"t\":\"sphere\",\"c\":%1,\"r\":%2%3%4}").arg(vec(ce), num(r), col(), cls(c)));
	}
	void drawTriangle(Vector3f p1, Vector3f p2, Vector3f p3, PrimitiveClass* c) override {
		put(QString("{\"t\":\"triangle\",\"p1\":%1,\"p2\":%2,\"p3\":%3%4%5}")
			.arg(vec(p1), vec(p2), vec(p3), col(), cls(c)));
	}
	void callGeneric(PrimitiveClass* c) override { put(QString("{\"t\":\"template\"%1}").arg(cls(c))); }
	void setColor(Vector3f v) override { rgb = v; }
	void setAlpha(double a) override { alpha = a; }
	void setPreviousColor(Vector3f v) override { prevRgb = v; }
	void setPreviousAlpha(double a) override { prevAlpha = a; }
	void setBackgroundColor(Vector3f v) override { put(QString("{\"ev\":\"background\",\"rgb\":%1}").arg(vec(v))); }
	void setTranslation(Vector3f v) override { put(QString("{\"ev\":\"translation\",\"v\":%1}").arg(vec(v))); }
	void setScale(double s) override { put(QString("{\"ev\":\"scale\",\"v\":%1}").arg(num(s))); }
	void setPivot(Vector3f v) override { put(QString("{\"ev\":\"pivot\",\"v\":%1}").arg(vec(v))); }
	void setPerspectiveAngle(double a) override { put(QString("{\"ev\":\"fov\",\"v\":%1}").arg(num(a))); }
	void setRotation(Matrix4f m) override {
		QStringList v;
		for (int r = 0; r < 3; r++) for (int c = 0; c < 3; c++) v << num(m(r, c));
		put("{\"ev\":\"rotation\",\"m\":[" + v.join(",") + "]}");
	}
};

// Reproduce VariableEditor::updateFromPreprocessor with real spin boxes (exact rounding/clamping).
static QString applyGuiParameters(Preprocessor& pp, QString in, QStringList& paramJson) {
	QMap<QString, QString> subs;
	for (GuiParameter* p : pp.getParameters()) {
		QString value;
		if (auto* f = dynamic_cast<FloatParameter*>(p)) {
			QDoubleSpinBox sb; sb.setMaximum(f->getTo()); sb.setMinimum(f->getFrom()); sb.setValue(f->getDefaultValue());
			value = QString::number(sb.value());
		} else if (auto* i = dynamic_cast<IntParameter*>(p)) {
			QSpinBox sb; sb.setMaximum(i->getTo()); sb.setMinimum(i->getFrom()); sb.setValue(i->getDefaultValue());
			value = QString::number(sb.value());
		}
		subs[p->getName()] = value;
		paramJson << QString("{\"name\":%1,\"value\":%2}").arg(jstr(p->getName()), jstr(value));
	}
	int subst = 0;
	auto it = subs.constBegin();
	while (it != subs.constEnd()) {
		if (subst > 100) break;
		if (in.contains(it.key())) { in.replace(it.key(), it.value()); it = subs.constBegin(); subst++; }
		else ++it;
	}
	return in;
}

int main(int argc, char** argv) {
	qputenv("QT_QPA_PLATFORM", "offscreen");
	QApplication app(argc, argv);
	if (argc < 5) { fprintf(stderr, "usage: golden_dump MODE SCRIPT SEED OUT [TEMPLATE]\n"); return 2; }
	QString mode = argv[1], script = argv[2], outPath = argv[4];
	int seed = QString(argv[3]).toInt();
	QFile f(script);
	if (!f.open(QFile::ReadOnly | QFile::Text)) return 3;
	QString text = QTextStream(&f).readAll();

	JsonLogger logger;
	QStringList params, meta;
	QString output, error;
	Renderer* renderer = nullptr;
	DumpRenderer dump;
	Template* tmpl = nullptr;
	TemplateRenderer* trender = nullptr;
	ObjRenderer objRenderer(10, 10, false, false);
	try {
		if (mode == "template") {
			QFile tf(argv[5]);
			tmpl = new Template(tf);
			trender = new TemplateRenderer(*tmpl);
			trender->setCamera(Vector3f(0, 0, 20), Vector3f(0, 1, 0), Vector3f(1, 0, 0), Vector3f(0, 0, 0),
				640, 480, 640 / 480.0, 22.0);
			trender->setBackgroundColor(Vector3f(0, 0, 0));
			renderer = trender;
		} else if (mode == "obj") {
			renderer = &objRenderer;
		} else {
			renderer = &dump;
		}
		renderer->begin();
		RandomStreams::SetSeed(seed);
		Preprocessor pp;
		QString out = pp.Process(text, seed);
		out = applyGuiParameters(pp, out, params);
		Tokenizer tokenizer(out);
		EisenParser parser(&tokenizer);
		RuleSet* rs = parser.parseRuleset();
		rs->resolveNames();
		Builder b(renderer, rs, true);
		b.build();
		renderer->end();
		QStringList cmds;
		for (const auto& c : b.getRaytracerCommands()) cmds << QString("[%1,%2]").arg(jstr(c.command), jstr(c.arg));
		meta << QString("\"raytracer\":[%1]").arg(cmds.join(","));
		meta << QString("\"seed_changed\":%1,\"new_seed\":%2").arg(b.seedChanged() ? "true" : "false").arg(b.getNewSeed());
	} catch (ParseError& pe) {
		error = QString("{\"kind\":\"parse\",\"message\":%1,\"pos\":%2}").arg(jstr(pe.getMessage())).arg(pe.getPosition());
	} catch (SyntopiaCore::Exceptions::Exception& e) {
		error = QString("{\"kind\":\"exception\",\"message\":%1}").arg(jstr(e.getMessage()));
	}
	QFile of(outPath);
	of.open(QFile::WriteOnly);
	QTextStream os(&of);
	if (mode == "template" && trender) os << trender->getOutput();
	else if (mode == "obj") objRenderer.writeToStream(os);
	else os << dump.out.join("\n") << "\n";
	os.flush();
	meta << QString("\"params\":[%1]").arg(params.join(","));
	meta << QString("\"logs\":[%1]").arg(logger.lines.join(","));
	meta << QString("\"error\":%1").arg(error.isEmpty() ? "null" : error);
	printf("{%s}\n", meta.join(",").toUtf8().constData());
	return 0;
}
