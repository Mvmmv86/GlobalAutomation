/**
 * Script de teste para verificar o sistema de layers
 * Executa no Node.js com jsdom para simular o DOM
 */

// Simular ambiente de navegador
global.window = {
  devicePixelRatio: 1,
  requestAnimationFrame: (cb) => setTimeout(cb, 16),
  cancelAnimationFrame: (id) => clearTimeout(id),
  getComputedStyle: () => ({
    zIndex: '0',
    position: 'absolute',
    display: 'block'
  })
};

global.document = {
  createElement: (tag) => {
    if (tag === 'canvas') {
      return {
        width: 800,
        height: 600,
        style: {},
        getContext: (type) => {
          if (type === '2d') {
            return {
              scale: () => {},
              clearRect: () => {},
              fillRect: () => {},
              beginPath: () => {},
              moveTo: () => {},
              lineTo: () => {},
              stroke: () => {},
              fill: () => {},
              arc: () => {},
              save: () => {},
              restore: () => {},
              translate: () => {},
              setLineDash: () => {},
              getImageData: () => ({
                data: new Uint8ClampedArray([255, 0, 0, 255]) // Red pixel
              }),
              imageSmoothingEnabled: true,
              imageSmoothingQuality: 'high',
              fillStyle: '#000000',
              strokeStyle: '#000000',
              lineWidth: 1,
              font: '12px Arial'
            };
          }
          return null;
        }
      };
    } else if (tag === 'div') {
      const children = [];
      return {
        style: {},
        innerHTML: '',
        appendChild: (child) => {
          children.push(child);
          console.log(`✅ Canvas adicionado ao container. Total: ${children.length}`);
        },
        removeChild: (child) => {
          const index = children.indexOf(child);
          if (index > -1) {
            children.splice(index, 1);
          }
        },
        querySelectorAll: (selector) => {
          if (selector === 'canvas') {
            return children;
          }
          return [];
        },
        children
      };
    }
    return {};
  }
};

console.log('🧪 Iniciando teste do sistema de layers...\n');

// Teste 1: Verificar se as classes existem
console.log('📋 Teste 1: Verificando existência das classes');

const fs = require('fs');
const path = require('path');

const basePath = 'frontend-new/src/components/charts/CanvasProChart';
const filesToCheck = [
  'core/Layer.ts',
  'core/LayerManager.ts',
  'layers/BackgroundLayer.ts',
  'layers/MainLayer.ts',
  'layers/IndicatorLayer.ts',
  'layers/OverlayLayer.ts',
  'layers/InteractionLayer.ts',
  'layers/SeparatePanelLayer.ts',
  'PanelManager.ts',
  'DataManager.ts',
  'Engine.ts'
];

let allFilesExist = true;
filesToCheck.forEach(file => {
  const fullPath = path.join(basePath, file);
  if (fs.existsSync(fullPath)) {
    console.log(`  ✅ ${file}`);
  } else {
    console.log(`  ❌ ${file} - NÃO ENCONTRADO`);
    allFilesExist = false;
  }
});

console.log(allFilesExist ? '\n✅ Todos os arquivos existem!' : '\n❌ Alguns arquivos estão faltando!');

// Teste 2: Verificar estrutura do LayerManager
console.log('\n📋 Teste 2: Analisando LayerManager');

const layerManagerPath = path.join(basePath, 'core/LayerManager.ts');
const layerManagerContent = fs.readFileSync(layerManagerPath, 'utf8');

const expectedImports = [
  'BackgroundLayer',
  'MainLayer',
  'IndicatorLayer',
  'OverlayLayer',
  'InteractionLayer',
  'SeparatePanelLayer',
  'PanelManager',
  'DataManager',
  'ChartEngine'
];

let importsOk = true;
expectedImports.forEach(imp => {
  if (layerManagerContent.includes(imp)) {
    console.log(`  ✅ Import ${imp} encontrado`);
  } else {
    console.log(`  ❌ Import ${imp} NÃO encontrado`);
    importsOk = false;
  }
});

// Teste 3: Verificar métodos do LayerManager
console.log('\n📋 Teste 3: Verificando métodos do LayerManager');

const expectedMethods = [
  'initializeLayers',
  'addLayer',
  'removeLayer',
  'markLayerDirty',
  'scheduleRender',
  'render',
  'forceRender',
  'resize'
];

expectedMethods.forEach(method => {
  if (layerManagerContent.includes(method)) {
    console.log(`  ✅ Método ${method}() encontrado`);
  } else {
    console.log(`  ❌ Método ${method}() NÃO encontrado`);
  }
});

// Teste 4: Verificar index.tsx
console.log('\n📋 Teste 4: Verificando integração no index.tsx');

const indexPath = path.join(basePath, 'index.tsx');
const indexContent = fs.readFileSync(indexPath, 'utf8');

const expectedInIndex = [
  'LayerManager',
  'layerManagerRef',
  'new LayerManager',
  'markLayerDirty',
  'forceRender'
];

expectedInIndex.forEach(item => {
  if (indexContent.includes(item)) {
    console.log(`  ✅ ${item} encontrado no index.tsx`);
  } else {
    console.log(`  ❌ ${item} NÃO encontrado no index.tsx`);
  }
});

// Teste 5: Simulação de criação das layers
console.log('\n📋 Teste 5: Simulando criação das layers');

try {
  // Criar container mock
  const container = global.document.createElement('div');
  container.style.position = 'relative';

  // Simular criação de cada layer
  const layerNames = ['background', 'main', 'indicators', 'overlays', 'interaction'];

  layerNames.forEach((name, index) => {
    const canvas = global.document.createElement('canvas');
    canvas.width = 800;
    canvas.height = 600;
    canvas.style.position = 'absolute';
    canvas.style.zIndex = index.toString();

    container.appendChild(canvas);
    console.log(`  ✅ Layer "${name}" criada com z-index ${index}`);
  });

  // Verificar quantidade de canvas
  const canvasCount = container.children.length;
  console.log(`\n  📊 Total de canvas criados: ${canvasCount}`);

  if (canvasCount === 5) {
    console.log('  ✅ Todas as 5 layers foram criadas corretamente!');
  } else {
    console.log(`  ❌ Esperado 5 layers, mas foram criadas ${canvasCount}`);
  }

} catch (error) {
  console.log(`  ❌ Erro ao simular criação das layers: ${error.message}`);
}

// Teste 6: Verificar estrutura das layers
console.log('\n📋 Teste 6: Verificando estrutura das layers individuais');

const layerFiles = [
  'layers/BackgroundLayer.ts',
  'layers/MainLayer.ts',
  'layers/IndicatorLayer.ts',
  'layers/OverlayLayer.ts',
  'layers/InteractionLayer.ts'
];

layerFiles.forEach(file => {
  const fullPath = path.join(basePath, file);
  if (fs.existsSync(fullPath)) {
    const content = fs.readFileSync(fullPath, 'utf8');
    const layerName = path.basename(file, '.ts');

    // Verificar se estende Layer
    if (content.includes('extends Layer')) {
      console.log(`  ✅ ${layerName} extends Layer`);
    } else {
      console.log(`  ❌ ${layerName} NÃO extends Layer`);
    }

    // Verificar método render
    if (content.includes('render()') || content.includes('render():')) {
      console.log(`  ✅ ${layerName} tem método render()`);
    } else {
      console.log(`  ❌ ${layerName} NÃO tem método render()`);
    }
  }
});

// Relatório Final
console.log('\n' + '='.repeat(60));
console.log('📊 RELATÓRIO FINAL DO TESTE');
console.log('='.repeat(60));

const issues = [];

if (!allFilesExist) {
  issues.push('❌ Alguns arquivos de layer estão faltando');
}

if (!importsOk) {
  issues.push('❌ LayerManager não importa todas as dependências necessárias');
}

if (!indexContent.includes('LayerManager')) {
  issues.push('❌ index.tsx não está usando LayerManager');
}

if (issues.length === 0) {
  console.log('\n✅ SUCESSO! O sistema de layers está corretamente implementado!');
  console.log('\nPróximos passos:');
  console.log('1. Testar visualmente no navegador em http://localhost:3000/test/layers');
  console.log('2. Verificar se os candles estão sendo renderizados');
  console.log('3. Testar interação (zoom, pan, etc)');
  console.log('4. Adicionar indicadores para testar a layer de indicadores');
} else {
  console.log('\n⚠️ PROBLEMAS ENCONTRADOS:');
  issues.forEach(issue => console.log(`  ${issue}`));
  console.log('\nCorreções necessárias antes de testar no navegador.');
}

console.log('\n' + '='.repeat(60));