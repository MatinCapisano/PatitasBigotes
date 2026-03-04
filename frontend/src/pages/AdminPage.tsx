import { useState } from "react";
import {
  type AdminSection,
  formatArs,
  useAdminCatalog,
  useAdminDiscounts,
  useAdminOrdersPayments,
  useAdminTurns
} from "../features/admin";
import {
  AdminSectionTabs,
  CatalogSection,
  DiscountsSection,
  OrdersPaymentsSection,
  TurnsSection
} from "../features/admin/components";

export function AdminPage() {
  const [adminSection, setAdminSection] = useState<AdminSection>("catalogo");

  const catalog = useAdminCatalog();
  const turns = useAdminTurns(adminSection);
  const discounts = useAdminDiscounts({
    adminSection,
    categories: catalog.categories,
    productsSorted: catalog.productsSorted,
    variantsByProduct: catalog.variantsByProduct
  });
  const ordersPayments = useAdminOrdersPayments({
    adminSection,
    variantOptions: catalog.variantOptions
  });

  return (
    <section>
      <h1 className="page-title">Panel Admin</h1>
      <p className="page-subtitle">Elegi que queres gestionar: catalogo, turnos, ordenes o pagos.</p>
      <AdminSectionTabs adminSection={adminSection} onSelect={setAdminSection} />

      {adminSection === "descuentos" && (
        <DiscountsSection
          discountsError={discounts.discountsError}
          discountsLoading={discounts.discountsLoading}
          discounts={discounts.discounts}
          showCreateDiscountForm={discounts.showCreateDiscountForm}
          setShowCreateDiscountForm={discounts.setShowCreateDiscountForm}
          loadDiscounts={discounts.loadDiscounts}
          newDiscountName={discounts.newDiscountName}
          setNewDiscountName={discounts.setNewDiscountName}
          newDiscountType={discounts.newDiscountType}
          setNewDiscountType={discounts.setNewDiscountType}
          newDiscountValue={discounts.newDiscountValue}
          setNewDiscountValue={discounts.setNewDiscountValue}
          newDiscountTarget={discounts.newDiscountTarget}
          setNewDiscountTarget={discounts.setNewDiscountTarget}
          newDiscountCategoryId={discounts.newDiscountCategoryId}
          setNewDiscountCategoryId={discounts.setNewDiscountCategoryId}
          categories={discounts.categories}
          newDiscountActive={discounts.newDiscountActive}
          setNewDiscountActive={discounts.setNewDiscountActive}
          showDiscountProductPicker={discounts.showDiscountProductPicker}
          setShowDiscountProductPicker={discounts.setShowDiscountProductPicker}
          selectedDiscountProductCount={discounts.selectedDiscountProductCount}
          selectedDiscountVariantCount={discounts.selectedDiscountVariantCount}
          productsSorted={discounts.productsSorted}
          variantsByProduct={discounts.variantsByProduct}
          discountPickerExpandedProducts={discounts.discountPickerExpandedProducts}
          toggleDiscountPickerProductExpanded={discounts.toggleDiscountPickerProductExpanded}
          selectedDiscountProductIds={discounts.selectedDiscountProductIds}
          selectedDiscountVariantIds={discounts.selectedDiscountVariantIds}
          toggleDiscountProductSelection={discounts.toggleDiscountProductSelection}
          toggleDiscountVariantSelection={discounts.toggleDiscountVariantSelection}
          onCreateDiscount={discounts.onCreateDiscount}
          onToggleDiscountActive={discounts.onToggleDiscountActive}
          onDeleteDiscount={discounts.onDeleteDiscount}
          formatArs={formatArs}
        />
      )}

      {adminSection === "catalogo" && (
        <CatalogSection
          error={catalog.error}
          showCreateProductForm={catalog.showCreateProductForm}
          setShowCreateProductForm={catalog.setShowCreateProductForm}
          onCreateProduct={catalog.onCreateProduct}
          savingNew={catalog.savingNew}
          newName={catalog.newName}
          setNewName={catalog.setNewName}
          newCategory={catalog.newCategory}
          setNewCategory={catalog.setNewCategory}
          categories={catalog.categories}
          newDescription={catalog.newDescription}
          setNewDescription={catalog.setNewDescription}
          newImgUrl={catalog.newImgUrl}
          setNewImgUrl={catalog.setNewImgUrl}
          loading={catalog.loading}
          productsSorted={catalog.productsSorted}
          variantsByProduct={catalog.variantsByProduct}
          expandedProducts={catalog.expandedProducts}
          toggleProductExpanded={catalog.toggleProductExpanded}
          openProductMenuId={catalog.openProductMenuId}
          setOpenProductMenuId={catalog.setOpenProductMenuId}
          onStartEdit={catalog.onStartEdit}
          onDeleteProduct={catalog.onDeleteProduct}
          editingProductId={catalog.editingProductId}
          editName={catalog.editName}
          setEditName={catalog.setEditName}
          editCategory={catalog.editCategory}
          setEditCategory={catalog.setEditCategory}
          editDescription={catalog.editDescription}
          setEditDescription={catalog.setEditDescription}
          editImgUrl={catalog.editImgUrl}
          setEditImgUrl={catalog.setEditImgUrl}
          editActive={catalog.editActive}
          setEditActive={catalog.setEditActive}
          onSaveProductEdit={catalog.onSaveProductEdit}
          setEditingProductId={catalog.setEditingProductId}
          editingVariantId={catalog.editingVariantId}
          onStartVariantEdit={catalog.onStartVariantEdit}
          editVariantSku={catalog.editVariantSku}
          setEditVariantSku={catalog.setEditVariantSku}
          editVariantSize={catalog.editVariantSize}
          setEditVariantSize={catalog.setEditVariantSize}
          editVariantColor={catalog.editVariantColor}
          setEditVariantColor={catalog.setEditVariantColor}
          editVariantImgUrl={catalog.editVariantImgUrl}
          setEditVariantImgUrl={catalog.setEditVariantImgUrl}
          editVariantStock={catalog.editVariantStock}
          setEditVariantStock={catalog.setEditVariantStock}
          editVariantActive={catalog.editVariantActive}
          setEditVariantActive={catalog.setEditVariantActive}
          enableVariantPriceEdit={catalog.enableVariantPriceEdit}
          setEnableVariantPriceEdit={catalog.setEnableVariantPriceEdit}
          editVariantPrice={catalog.editVariantPrice}
          setEditVariantPrice={catalog.setEditVariantPrice}
          onSaveVariantEdit={catalog.onSaveVariantEdit}
          setEditingVariantId={catalog.setEditingVariantId}
          formatArs={formatArs}
        />
      )}

      {adminSection === "turnos" && (
        <TurnsSection
          turns={turns.turns}
          turnsError={turns.turnsError}
          turnsFilter={turns.turnsFilter}
          setTurnsFilter={turns.setTurnsFilter}
          loadTurns={turns.loadTurns}
          onUpdateTurnStatus={turns.onUpdateTurnStatus}
        />
      )}

      {(adminSection === "ordenes" || adminSection === "pagos") && (
        <OrdersPaymentsSection
          adminSection={adminSection}
          orderError={ordersPayments.orderError}
          orderSuccess={ordersPayments.orderSuccess}
          showCreateManualOrderForm={ordersPayments.showCreateManualOrderForm}
          setShowCreateManualOrderForm={ordersPayments.setShowCreateManualOrderForm}
          ordersFilter={ordersPayments.ordersFilter}
          setOrdersFilter={ordersPayments.setOrdersFilter}
          ordersSortBy={ordersPayments.ordersSortBy}
          setOrdersSortBy={ordersPayments.setOrdersSortBy}
          ordersSortDir={ordersPayments.ordersSortDir}
          setOrdersSortDir={ordersPayments.setOrdersSortDir}
          ordersShowAll={ordersPayments.ordersShowAll}
          setOrdersShowAll={ordersPayments.setOrdersShowAll}
          manualEmail={ordersPayments.manualEmail}
          setManualEmail={ordersPayments.setManualEmail}
          manualFirstName={ordersPayments.manualFirstName}
          setManualFirstName={ordersPayments.setManualFirstName}
          manualLastName={ordersPayments.manualLastName}
          setManualLastName={ordersPayments.setManualLastName}
          manualPhone={ordersPayments.manualPhone}
          setManualPhone={ordersPayments.setManualPhone}
          manualVariantId={ordersPayments.manualVariantId}
          setManualVariantId={ordersPayments.setManualVariantId}
          manualQuantity={ordersPayments.manualQuantity}
          setManualQuantity={ordersPayments.setManualQuantity}
          variantOptions={catalog.variantOptions}
          onAddManualItem={ordersPayments.onAddManualItem}
          manualItems={ordersPayments.manualItems}
          removeManualItem={ordersPayments.removeManualItem}
          setManualItems={ordersPayments.setManualItems}
          onCreateManualOrder={ordersPayments.onCreateManualOrder}
          ordersListLoading={ordersPayments.ordersListLoading}
          ordersList={ordersPayments.ordersList}
          loadAdminOrder={ordersPayments.loadAdminOrder}
          paymentsFilter={ordersPayments.paymentsFilter}
          setPaymentsFilter={ordersPayments.setPaymentsFilter}
          paymentsSortBy={ordersPayments.paymentsSortBy}
          setPaymentsSortBy={ordersPayments.setPaymentsSortBy}
          paymentsSortDir={ordersPayments.paymentsSortDir}
          setPaymentsSortDir={ordersPayments.setPaymentsSortDir}
          paymentsShowAll={ordersPayments.paymentsShowAll}
          setPaymentsShowAll={ordersPayments.setPaymentsShowAll}
          showManualPaymentForm={ordersPayments.showManualPaymentForm}
          setShowManualPaymentForm={ordersPayments.setShowManualPaymentForm}
          paymentsListLoading={ordersPayments.paymentsListLoading}
          paymentsList={ordersPayments.paymentsList}
          selectedOrder={ordersPayments.selectedOrder}
          orderPayments={ordersPayments.orderPayments}
          manualPayRef={ordersPayments.manualPayRef}
          setManualPayRef={ordersPayments.setManualPayRef}
          manualPayAmount={ordersPayments.manualPayAmount}
          setManualPayAmount={ordersPayments.setManualPayAmount}
          onMarkOrderPaid={ordersPayments.onMarkOrderPaid}
          formatArs={formatArs}
        />
      )}
    </section>
  );
}
