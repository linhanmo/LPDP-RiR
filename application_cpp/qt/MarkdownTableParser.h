#pragma once

#include <QString>
#include <QStringList>
#include <QVector>

struct MarkdownTable
{
  QString title;
  QStringList headers;
  QVector<QStringList> rows;
};

QVector<MarkdownTable> parseMarkdownTables(const QString &md);
