// Test-harness stub: replaces the OpenGL-dependent original; keeps only what the model code needs.
#pragma once
#include <QtCore>
#include <QColor>  // the original pulled these in transitively via <QtOpenGL>
#include <QImage>
#include "../Math/Vector3.h"
namespace SyntopiaCore {
	namespace GLEngine {
		struct PrimitiveClass {
			PrimitiveClass() : reflection(0), hasShadows(true), castShadows(true),
				ambient(0.6), specular(0.6), diffuse(0.6) {}
			QString name;
			double reflection;
			bool hasShadows;
			bool castShadows;
			double ambient;
			double specular;
			double diffuse;
		};
	}
}
