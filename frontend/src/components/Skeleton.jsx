/**
 * Skeleton loader components.
 * One base element + page-specific layouts for all 7 pages.
 */

const pulse = {
  background: 'linear-gradient(90deg, #EBEBEB 25%, #E0E0E0 50%, #EBEBEB 75%)',
  backgroundSize: '200% 100%',
  animation: 'skeleton-shimmer 1.5s infinite',
  borderRadius: '6px',
}

// Inject keyframes once
if (typeof document !== 'undefined' && !document.getElementById('skeleton-style')) {
  const style = document.createElement('style')
  style.id = 'skeleton-style'
  style.textContent = `
    @keyframes skeleton-shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `
  document.head.appendChild(style)
}

// ── Base element ──────────────────────────────────────────
export function Bone({ w = '100%', h = '16px', radius = '6px', style = {} }) {
  return (
    <div style={{
      ...pulse,
      width: w,
      height: h,
      borderRadius: radius,
      flexShrink: 0,
      ...style,
    }} />
  )
}

// ── Card wrapper ──────────────────────────────────────────
function SkelCard({ children, style = {} }) {
  return (
    <div style={{
      background: 'var(--bg-card)',
      border: '1px solid var(--border)',
      borderRadius: '10px',
      padding: '24px',
      ...style,
    }}>
      {children}
    </div>
  )
}

// ── Row helper ────────────────────────────────────────────
function Row({ children, gap = 16, mb = 0 }) {
  return (
    <div style={{
      display: 'flex',
      gap,
      marginBottom: mb,
      alignItems: 'flex-start',
    }}>
      {children}
    </div>
  )
}

// ── Grid helper ───────────────────────────────────────────
function Grid({ children, cols = '1fr 1fr', gap = 20, mb = 20 }) {
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: cols,
      gap,
      marginBottom: mb,
    }}>
      {children}
    </div>
  )
}

// ── Table rows ────────────────────────────────────────────
function SkelTableRows({ rows = 4, cols = 4 }) {
  return (
    <div style={{ marginTop: '12px' }}>
      {/* Header */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: `repeat(${cols}, 1fr)`,
        gap: '12px',
        paddingBottom: '12px',
        borderBottom: '1px solid var(--border)',
        marginBottom: '8px',
      }}>
        {Array.from({ length: cols }).map((_, i) => (
          <Bone key={i} h="10px" w="60%" />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${cols}, 1fr)`,
          gap: '12px',
          padding: '12px 0',
          borderBottom: '1px solid var(--border)',
        }}>
          {Array.from({ length: cols }).map((_, j) => (
            <Bone key={j} h="13px" w={j === 0 ? '40%' : j === cols - 1 ? '55%' : '80%'} />
          ))}
        </div>
      ))}
    </div>
  )
}

// ── Page skeletons ────────────────────────────────────────

export function OverviewSkeleton() {
  return (
    <div>
      {/* Page header */}
      <div style={{ marginBottom: '32px' }}>
        <Bone w="280px" h="24px" style={{ marginBottom: '10px' }} />
        <Bone w="160px" h="14px" />
      </div>

      {/* Target banner */}
      <SkelCard style={{ marginBottom: '32px', padding: '28px 32px' }}>
        <Row mb={24}>
          <div style={{ flex: 1 }}>
            <Bone w="120px" h="10px" style={{ marginBottom: '8px' }} />
            <Bone w="340px" h="14px" />
          </div>
          <Bone w="80px" h="32px" />
        </Row>
        <Grid cols="repeat(4, 1fr)" gap={12} mb={28}>
          {[1,2,3,4].map((i) => (
            <div key={i} style={{
              background: 'var(--bg-elevated)',
              borderRadius: '8px',
              padding: '20px 24px',
            }}>
              <Bone w="60px" h="10px" style={{ marginBottom: '12px' }} />
              <Bone w="80px" h="26px" style={{ marginBottom: '6px' }} />
              <Bone w="100px" h="11px" />
            </div>
          ))}
        </Grid>
        <Bone w="100%" h="6px" radius="3px" />
      </SkelCard>

      {/* Middle row */}
      <Grid cols="repeat(auto-fit, minmax(300px, 1fr))" mb={24}>
        <SkelCard>
          <Bone w="140px" h="15px" style={{ marginBottom: '20px' }} />
          <Bone w="100%" h="220px" radius="8px" style={{ marginBottom: '12px' }} />
          <Row gap={20} style={{ justifyContent: 'center' }}>
            {[1,2,3].map((i) => <Bone key={i} w="60px" h="12px" />)}
          </Row>
        </SkelCard>
        <Grid cols="1fr 1fr" gap={16}>
          {[1,2,3,4].map((i) => (
            <SkelCard key={i}>
              <Bone w="80px" h="11px" style={{ marginBottom: '12px' }} />
              <Bone w="100px" h="30px" style={{ marginBottom: '8px' }} />
              <Bone w="120px" h="12px" />
            </SkelCard>
          ))}
        </Grid>
      </Grid>

      {/* Bottom row */}
      <Grid cols="repeat(auto-fit, minmax(300px, 1fr))">
        <SkelCard>
          <Bone w="160px" h="15px" style={{ marginBottom: '20px' }} />
          <SkelTableRows rows={3} cols={4} />
        </SkelCard>
        <SkelCard>
          <Bone w="180px" h="15px" style={{ marginBottom: '20px' }} />
          <Bone w="100%" h="220px" radius="8px" />
        </SkelCard>
      </Grid>
    </div>
  )
}

export function TrendsSkeleton() {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <Bone w="120px" h="24px" style={{ marginBottom: '10px' }} />
        <Bone w="220px" h="14px" />
      </div>

      {/* Filter bar */}
      <Row mb={24} gap={12}>
        <Bone w="120px" h="34px" />
        <Bone w="100px" h="34px" />
        <Bone w="100px" h="34px" />
        <Bone w="100px" h="34px" />
      </Row>

      {/* Charts */}
      <SkelCard style={{ marginBottom: '20px' }}>
        <Bone w="160px" h="15px" style={{ marginBottom: '20px' }} />
        <Bone w="100%" h="260px" radius="8px" />
      </SkelCard>
      <SkelCard>
        <Bone w="200px" h="15px" style={{ marginBottom: '20px' }} />
        <Bone w="100%" h="220px" radius="8px" />
      </SkelCard>
    </div>
  )
}

export function SitesSkeleton() {
  return (
    <div>
      <Row mb={28} style={{ justifyContent: 'space-between' }}>
        <div>
          <Bone w="180px" h="24px" style={{ marginBottom: '10px' }} />
          <Bone w="220px" h="14px" />
        </div>
        <Bone w="100px" h="36px" />
      </Row>

      {/* Map */}
      <div style={{
        borderRadius: '10px',
        overflow: 'hidden',
        border: '1px solid var(--border)',
        marginBottom: '20px',
      }}>
        <Bone w="100%" h="500px" radius="0" />
        <div style={{
          padding: '10px 20px',
          background: 'var(--bg-surface)',
          borderTop: '1px solid var(--border)',
          display: 'flex',
          gap: '16px',
          alignItems: 'center',
        }}>
          <Bone w="120px" h="10px" />
          {[1,2,3].map((i) => <Bone key={i} w="70px" h="10px" />)}
        </div>
      </div>

      {/* Charts */}
      <Grid cols="repeat(auto-fit, minmax(280px, 1fr))" mb={20}>
        <SkelCard>
          <Bone w="160px" h="15px" style={{ marginBottom: '20px' }} />
          <Bone w="100%" h="180px" radius="8px" />
        </SkelCard>
        <SkelCard>
          <Bone w="180px" h="15px" style={{ marginBottom: '20px' }} />
          <Bone w="100%" h="180px" radius="8px" />
        </SkelCard>
      </Grid>

      {/* Table */}
      <SkelCard>
        <Bone w="100px" h="15px" style={{ marginBottom: '20px' }} />
        <SkelTableRows rows={4} cols={6} />
      </SkelCard>
    </div>
  )
}

export function FactorsSkeleton() {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <Bone w="180px" h="24px" style={{ marginBottom: '10px' }} />
        <Bone w="280px" h="14px" />
      </div>

      {/* Summary cards */}
      <Row mb={24} gap={16}>
        {[1,2,3,4].map((i) => (
          <SkelCard key={i} style={{ flex: 1, textAlign: 'center' }}>
            <Bone w="40px" h="24px" style={{ margin: '0 auto 8px' }} />
            <Bone w="70px" h="11px" style={{ margin: '0 auto' }} />
          </SkelCard>
        ))}
      </Row>

      {/* Filters */}
      <Row mb={20} gap={12}>
        <Bone w="260px" h="36px" />
        <Bone w="180px" h="36px" />
      </Row>

      {/* Table */}
      <SkelCard style={{ padding: 0 }}>
        <div style={{ padding: '20px 24px' }}>
          <SkelTableRows rows={8} cols={6} />
        </div>
      </SkelCard>
    </div>
  )
}

export function DataManagementSkeleton() {
  return (
    <div>
      <Row mb={32} style={{ justifyContent: 'space-between' }}>
        <div>
          <Bone w="200px" h="24px" style={{ marginBottom: '10px' }} />
          <Bone w="280px" h="14px" />
        </div>
        <Bone w="160px" h="36px" />
      </Row>

      {/* Upload zone */}
      <SkelCard style={{ marginBottom: '24px' }}>
        <Bone w="120px" h="15px" style={{ marginBottom: '16px' }} />
        <div style={{
          border: '2px dashed var(--border)',
          borderRadius: '8px',
          padding: '48px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: '12px',
        }}>
          <Bone w="32px" h="32px" radius="50%" />
          <Bone w="240px" h="14px" />
          <Bone w="180px" h="12px" />
        </div>
      </SkelCard>

      {/* Process pending */}
      <SkelCard style={{ marginBottom: '24px' }}>
        <Row style={{ justifyContent: 'space-between' }} gap={16}>
          <div style={{ flex: 1 }}>
            <Bone w="200px" h="15px" style={{ marginBottom: '8px' }} />
            <Bone w="320px" h="13px" style={{ marginBottom: '10px' }} />
            <Bone w="260px" h="12px" />
          </div>
          <Bone w="180px" h="38px" />
        </Row>
      </SkelCard>

      {/* History table */}
      <SkelCard>
        <Bone w="140px" h="15px" style={{ marginBottom: '20px' }} />
        <SkelTableRows rows={3} cols={7} />
      </SkelCard>
    </div>
  )
}

export function FlagsSkeleton() {
  return (
    <div>
      <div style={{ marginBottom: '32px' }}>
        <Bone w="200px" h="24px" style={{ marginBottom: '10px' }} />
        <Bone w="320px" h="14px" />
      </div>

      {/* Summary cards */}
      <Row mb={32} gap={16}>
        {[1,2,3].map((i) => (
          <SkelCard key={i} style={{ flex: 1, padding: '20px 24px' }}>
            <Bone w="80px" h="11px" style={{ marginBottom: '10px' }} />
            <Bone w="40px" h="28px" style={{ marginBottom: '6px' }} />
            <Bone w="110px" h="11px" />
          </SkelCard>
        ))}
      </Row>

      {/* Tabs + filter */}
      <Row mb={16} style={{ justifyContent: 'space-between' }}>
        <Row gap={4}>
          <Bone w="130px" h="34px" />
          <Bone w="110px" h="34px" />
        </Row>
        <Bone w="140px" h="34px" />
      </Row>

      {/* Table */}
      <SkelCard style={{ padding: 0 }}>
        <div style={{ padding: '0 24px' }}>
          <SkelTableRows rows={5} cols={8} />
        </div>
      </SkelCard>
    </div>
  )
}

export function ReportsSkeleton() {
  return (
    <div>
      <Row mb={24} style={{ justifyContent: 'space-between' }}>
        <div>
          <Bone w="120px" h="24px" style={{ marginBottom: '10px' }} />
          <Bone w="280px" h="14px" />
        </div>
        <Bone w="120px" h="36px" />
      </Row>

      {/* Org context */}
      <SkelCard style={{ marginBottom: '24px', padding: '16px 20px' }}>
        <Row style={{ justifyContent: 'space-between' }}>
          <div>
            <Bone w="100px" h="10px" style={{ marginBottom: '6px' }} />
            <Bone w="200px" h="15px" style={{ marginBottom: '4px' }} />
            <Bone w="240px" h="12px" />
          </div>
          <Row gap={8}>
            <Bone w="100px" h="24px" radius="20px" />
            <Bone w="110px" h="24px" radius="20px" />
          </Row>
        </Row>
      </SkelCard>

      {/* Report cards */}
      <Grid cols="repeat(auto-fit, minmax(280px, 1fr))" mb={24}>
        {[1,2,3].map((i) => (
          <SkelCard key={i} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <Row style={{ justifyContent: 'space-between' }}>
              <Bone w="160px" h="15px" />
              <Bone w="50px" h="22px" radius="20px" />
            </Row>
            <Bone w="100%" h="13px" />
            <Bone w="80%" h="13px" />
            <Bone w="60%" h="13px" />
            <Row style={{ justifyContent: 'space-between', marginTop: '8px' }}>
              <Bone w="120px" h="12px" />
              <Bone w="70px" h="32px" />
            </Row>
          </SkelCard>
        ))}
      </Grid>

      {/* Methodology */}
      <SkelCard>
        <Bone w="200px" h="15px" style={{ marginBottom: '16px' }} />
        {[1,2,3,4].map((i) => (
          <Bone key={i} w={i % 2 === 0 ? '90%' : '100%'} h="13px" style={{ marginBottom: '8px' }} />
        ))}
      </SkelCard>
    </div>
  )
}
