#include "MarkdownTableParser.h"

#include <QStringView>

namespace
{
  QStringList splitRow(const QString &line)
  {
    QString s = line.trimmed();
    if (s.startsWith('|'))
      s.remove(0, 1);
    if (s.endsWith('|'))
      s.chop(1);
    QStringList parts = s.split('|');
    for (auto &p : parts)
    {
      p = p.trimmed();
    }
    return parts;
  }

  bool looksLikeSeparatorRow(const QString &line)
  {
    const QString s = line.trimmed();
    if (!s.startsWith('|'))
      return false;
    return s.contains('-');
  }

  bool looksLikeTableRow(const QString &line)
  {
    const QString s = line.trimmed();
    return s.startsWith('|') && s.count('|') >= 2;
  }
}

QVector<MarkdownTable> parseMarkdownTables(const QString &md)
{
  const QStringList lines = md.split('\n');
  QVector<MarkdownTable> tables;

  int i = 0;
  QString currentTitle;
  while (i < lines.size())
  {
    const QString line = lines[i].trimmed();
    if (line.startsWith("## "))
    {
      currentTitle = line.mid(3).trimmed();
      ++i;
      continue;
    }

    if (!currentTitle.isEmpty() && looksLikeTableRow(line))
    {
      const QStringList headerCells = splitRow(line);

      if (i + 1 < lines.size() && looksLikeTableRow(lines[i + 1]))
      {
        if (looksLikeSeparatorRow(lines[i + 1]))
        {
          i += 2;
        }
        else
        {
          i += 1;
        }
      }
      else
      {
        i += 1;
      }

      QVector<QStringList> rows;
      while (i < lines.size())
      {
        const QString rowLine = lines[i].trimmed();
        if (!rowLine.startsWith('|'))
          break;
        QStringList rowCells = splitRow(rowLine);
        while (rowCells.size() < headerCells.size())
          rowCells.append("");
        while (rowCells.size() > headerCells.size())
          rowCells.removeLast();
        rows.push_back(rowCells);
        ++i;
      }

      MarkdownTable t;
      t.title = currentTitle;
      t.headers = headerCells;
      t.rows = rows;
      tables.push_back(t);
      currentTitle.clear();
      continue;
    }

    ++i;
  }

  return tables;
}
