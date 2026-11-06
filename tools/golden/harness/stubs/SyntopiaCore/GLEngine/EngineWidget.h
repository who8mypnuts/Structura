// Test-harness stub: only the Command record used by Builder.
#pragma once
#include <QString>
#include "Object3D.h"
namespace SyntopiaCore {
	namespace GLEngine {
		struct Command {
			Command() {}
			Command(QString command, QString arg) : command(command), arg(arg) {}
			QString command;
			QString arg;
		};
	}
}
