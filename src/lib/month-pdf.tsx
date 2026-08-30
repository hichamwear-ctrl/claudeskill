import { Document, Page, Text, View, StyleSheet, renderToBuffer } from "@react-pdf/renderer";
import { formatEuros, monthNetRemainder } from "@/core/finance";
import { prisma } from "./db";

const styles = StyleSheet.create({
  page: { padding: 32, fontSize: 11, color: "#1a1a1a" },
  title: { fontSize: 20, marginBottom: 4, fontWeight: 700 },
  sub: { fontSize: 11, color: "#666", marginBottom: 16 },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    paddingVertical: 6,
    borderBottom: "1px solid #e5e5e5",
  },
  name: { color: "#333" },
  amount: { fontWeight: 700 },
  total: { flexDirection: "row", justifyContent: "space-between", marginTop: 18 },
  totalLabel: { fontSize: 13, fontWeight: 700 },
  totalValue: { fontSize: 15, fontWeight: 700 },
});

/** Rendu serveur du récapitulatif mensuel en PDF. Renvoie un Buffer. */
export async function renderMonthPdf(monthId: string): Promise<Buffer | null> {
  const month = await prisma.month.findUnique({
    where: { id: monthId },
    include: { expenses: { include: { category: true }, orderBy: { createdAt: "asc" } } },
  });
  if (!month) return null;

  const remainder = monthNetRemainder(
    month.clientPayment,
    month.expenses.map((e) => ({ amount: e.amount, type: e.category.type })),
  );

  const doc = (
    <Document>
      <Page size="A4" style={styles.page}>
        <Text style={styles.title}>{month.label}</Text>
        <Text style={styles.sub}>Récapitulatif du mois</Text>

        <View style={styles.row}>
          <Text style={styles.name}>Revenu</Text>
          <Text style={styles.amount}>{formatEuros(month.clientPayment)}</Text>
        </View>

        {month.expenses.map((e) => {
          const signed = e.category.type === "ADDITION" ? e.amount : -e.amount;
          return (
            <View style={styles.row} key={e.id}>
              <Text style={styles.name}>{e.category.name}</Text>
              <Text style={styles.amount}>{formatEuros(signed)}</Text>
            </View>
          );
        })}

        <View style={styles.total}>
          <Text style={styles.totalLabel}>Reste net du mois</Text>
          <Text style={styles.totalValue}>{formatEuros(remainder)}</Text>
        </View>
      </Page>
    </Document>
  );

  return renderToBuffer(doc);
}
