// CPS tilemap layer dumper (Richard) - exporte les layers en PPM vraies couleurs
// depuis la RAM vive. Appele par touches dans le frontend.
// Scroll1 (8x8), Scroll2 (16x16), Scroll3 (32x32). Sortie PPM -> PNG via python.
#include "cps.h"
#include <stdio.h>

// Lit un pixel d'un tile dans CpsGfx (format FBNeo planar deplie).
// lineBytes = (sizepx/8)*4 ; groupe 8px = 1 u32 (4 octets) ; pixel = nibble MSB.
static inline int tile_pixel(UINT32 tileAddr, int px, int py, int sizepx)
{
	int groupsPerLine = sizepx / 8;
	int lineBytes = groupsPerLine * 4;
	int grp = px / 8;
	int inGrp = px & 7;
	UINT32 base = tileAddr + (UINT32)py * lineBytes + (UINT32)grp * 4;
	if (base + 3 >= nCpsGfxLen) return 0;
	UINT32 b = CpsGfx[base] | (CpsGfx[base+1]<<8) | (CpsGfx[base+2]<<16) | (CpsGfx[base+3]<<24);
	return (b >> (28 - inGrp*4)) & 0xF;
}

// Dump generique d'un layer. layer = 1, 2 ou 3.
static INT32 DumpLayer(const char* filename, int layer)
{
	if (CpsSaveReg[0] == NULL || CpsGfx == NULL) return 1;

	int regOff, tileShift, palBase, TS, scrollIdx;
	switch (layer) {
		case 1: regOff=0x02; tileShift=6; palBase=0x20; TS=8;  scrollIdx=1; break;
		case 2: regOff=0x04; tileShift=7; palBase=0x40; TS=16; scrollIdx=2; break;
		default:regOff=0x06; tileShift=9; palBase=0x60; TS=32; scrollIdx=3; break;
	}

	INT32 nOff = BURN_ENDIAN_SWAP_INT16(*((UINT16 *)(CpsSaveReg[0] + regOff)));
	nOff <<= 8; nOff &= 0xffc000;
	UINT8* Base = CpsFindGfxRam(nOff, 0x4000);
	if (Base == NULL) return 2;

	const int NT = 64;                 // 64 tiles dans chaque dimension
	const int W = NT * TS, H = NT * TS;

	FILE* f = fopen(filename, "wb");
	if (!f) return 3;
	fprintf(f, "P6\n%d %d\n255\n", W, H);
	unsigned char* row = (unsigned char*)malloc(W * 3);
	if (!row) { fclose(f); return 4; }

	for (int ty = 0; ty < NT; ty++) {
		for (int py = 0; py < TS; py++) {
			for (int tx = 0; tx < NT; tx++) {
				int fx = tx, fy = ty;
				INT32 p;
				if (layer == 1)      p = ((fy & 0x20) << 8) | ((fx & 0x3F) << 7) | ((fy & 0x1F) << 2);
				else if (layer == 2) p = ((fy & 0x30) << 8) | ((fx & 0x3F) << 6) | ((fy & 0x0F) << 2);
				else                 p = ((fy & 0x38) << 8) | ((fx & 0x3F) << 5) | ((fy & 0x07) << 2);
				p &= 0x3FFF;
				UINT16* pst = (UINT16 *)(Base + p);
				INT32 t = BURN_ENDIAN_SWAP_INT16(pst[0]);
				t <<= tileShift;
				t += nCpsGfxScroll[scrollIdx];
				INT32 a = BURN_ENDIAN_SWAP_INT16(pst[1]);
				INT32 palno = palBase | (a & 0x1F);
				int flipx = (a >> 5) & 1;
				int flipy = (a >> 6) & 1;

				for (int px = 0; px < TS; px++) {
					int sx = flipx ? (TS-1-px) : px;
					int sy = flipy ? (TS-1-py) : py;
					int idx = tile_pixel(t, sx, sy, TS);
					int r=0,g=0,b=0;
					if (CpsPal) {
						UINT32 col = CpsPal[(palno*16 + idx) & 0xfff];
						r = (col >> 16) & 0xFF; g = (col >> 8) & 0xFF; b = col & 0xFF;
					} else { r=g=b=idx*17; }
					int ox = (tx*TS + px) * 3;
					row[ox]=r; row[ox+1]=g; row[ox+2]=b;
				}
			}
			fwrite(row, 1, W*3, f);
		}
	}
	free(row);
	fclose(f);
	return 0;
}

extern "C" INT32 CpsDumpScroll3(const char* filename) { return DumpLayer(filename, 3); }

// ------------------------------------------------------------------------
// Dump par calques ALIGNES en espace ecran, avec transparence (Richard).
// Chaque layer est rendu dans le MEME canevas (donc deja cale), index 0 =
// transparent. Sortie RGBA brute : header "RGBA <W> <H>\n" puis W*H*4 octets.
// Canevas elargi (DUMP_MARGIN_X de chaque cote) pour voir/peindre les zones 16:9.
// ------------------------------------------------------------------------
// Canevas LARGE pour capturer toute la zone dispo hors-ecran (gauche+droite+haut+bas).
// Le rendu courant (nCpsScreenWidth x nCpsScreenHeight, ex 448x224 avec patch widescreen)
// est CENTRE dans le canevas -> marges symetriques = decor hors-ecran de chaque cote.
#define DUMP_OUT_W     768
#define DUMP_OUT_H     448

static INT32 DumpLayerScreen(const char* filename, int layer)
{
	if (CpsSaveReg[0] == NULL || CpsGfx == NULL) return 1;

	// Marges = centre le rendu courant dans le canevas (sx=0 = colonne 0 du rendu).
	const int marginX = (DUMP_OUT_W - nCpsScreenWidth)  / 2;
	const int marginY = (DUMP_OUT_H - nCpsScreenHeight) / 2;

	int regOff, regX, regY, tileShift, palBase, TS, scrollIdx, Wpx, Hpx, lXo, lYo;
	switch (layer) {
		case 1: regOff=0x02; regX=0x0c; regY=0x0e; tileShift=6; palBase=0x20; TS=8;  scrollIdx=1; Wpx=512;  Hpx=512;  lXo=CpsLayer1XOffs; lYo=CpsLayer1YOffs; break;
		case 2: regOff=0x04; regX=0x10; regY=0x12; tileShift=7; palBase=0x40; TS=16; scrollIdx=2; Wpx=1024; Hpx=1024; lXo=CpsLayer2XOffs; lYo=CpsLayer2YOffs; break;
		default:regOff=0x06; regX=0x14; regY=0x16; tileShift=9; palBase=0x60; TS=32; scrollIdx=3; Wpx=2048; Hpx=2048; lXo=CpsLayer3XOffs; lYo=CpsLayer3YOffs; break;
	}

	INT32 nOff = BURN_ENDIAN_SWAP_INT16(*((UINT16 *)(CpsSaveReg[0] + regOff)));
	nOff <<= 8; nOff &= 0xffc000;
	UINT8* Base = CpsFindGfxRam(nOff, 0x4000);
	if (Base == NULL) return 2;

	INT32 nScrX = BURN_ENDIAN_SWAP_INT16(*((UINT16 *)(CpsSaveReg[0] + regX)));
	INT32 nScrY = BURN_ENDIAN_SWAP_INT16(*((UINT16 *)(CpsSaveReg[0] + regY)));
	nScrX += 0x40 - nCpsGlobalXOffset + lXo;
	nScrY += 0x10 - nCpsGlobalYOffset + lYo;

	FILE* f = fopen(filename, "wb");
	if (!f) return 3;
	fprintf(f, "RGBA %d %d\n", DUMP_OUT_W, DUMP_OUT_H);
	unsigned char* row = (unsigned char*)malloc(DUMP_OUT_W * 4);
	if (!row) { fclose(f); return 4; }

	const int maskX = Wpx - 1, maskY = Hpx - 1;

	for (int oy = 0; oy < DUMP_OUT_H; oy++) {
		int sy  = oy - marginY;
		int tmy = (nScrY + sy) & maskY;
		int fy  = tmy / TS;
		int inTy = tmy & (TS - 1);
		for (int ox = 0; ox < DUMP_OUT_W; ox++) {
			int sx  = ox - marginX;
			int tmx = (nScrX + sx) & maskX;
			int fx  = tmx / TS;
			int inTx = tmx & (TS - 1);

			INT32 p;
			if (layer == 1)      p = ((fy & 0x20) << 8) | ((fx & 0x3F) << 7) | ((fy & 0x1F) << 2);
			else if (layer == 2) p = ((fy & 0x30) << 8) | ((fx & 0x3F) << 6) | ((fy & 0x0F) << 2);
			else                 p = ((fy & 0x38) << 8) | ((fx & 0x3F) << 5) | ((fy & 0x07) << 2);
			p &= 0x3FFF;
			UINT16* pst = (UINT16 *)(Base + p);
			INT32 t = BURN_ENDIAN_SWAP_INT16(pst[0]);
			t <<= tileShift;
			t += nCpsGfxScroll[scrollIdx];
			INT32 a = BURN_ENDIAN_SWAP_INT16(pst[1]);
			INT32 palno = palBase | (a & 0x1F);
			int flipx = (a >> 5) & 1;
			int flipy = (a >> 6) & 1;

			int srcx = flipx ? (TS - 1 - inTx) : inTx;
			int srcy = flipy ? (TS - 1 - inTy) : inTy;
			int idx = tile_pixel(t, srcx, srcy, TS);

			unsigned char r=0, g=0, b=0, al=0;
			if (idx != 0) {                 // 0 = transparent (couleur 0 du bloc)
				al = 255;
				if (CpsPal) {
					UINT32 col = CpsPal[(palno*16 + idx) & 0xfff];
					r=(col>>16)&0xFF; g=(col>>8)&0xFF; b=col&0xFF;
				} else { r=g=b=idx*17; }
			}
			int o = ox * 4;
			row[o]=r; row[o+1]=g; row[o+2]=b; row[o+3]=al;
		}
		fwrite(row, 1, DUMP_OUT_W*4, f);
	}
	free(row);
	fclose(f);
	return 0;
}

// Dump les 3 calques alignes d'un stage. Index auto-incremente -> stageNN_*.bin.
extern "C" INT32 CpsDumpStageLayers()
{
	static int stageIdx = 0;
	char fn[256];
	snprintf(fn, sizeof(fn), "stage%02d_scroll1.bin", stageIdx); INT32 r1 = DumpLayerScreen(fn, 1);
	snprintf(fn, sizeof(fn), "stage%02d_scroll2.bin", stageIdx); INT32 r2 = DumpLayerScreen(fn, 2);
	snprintf(fn, sizeof(fn), "stage%02d_scroll3.bin", stageIdx); INT32 r3 = DumpLayerScreen(fn, 3);

	// Metadata geometrie : permet a l'assembleur de placer EXACTEMENT les reperes
	// "sans patch" (384x224 natif) et "avec patch" (rendu courant nCpsScreenWidth).
	snprintf(fn, sizeof(fn), "stage%02d.meta", stageIdx);
	FILE* m = fopen(fn, "w");
	if (m) {
		int marginX = (DUMP_OUT_W - nCpsScreenWidth)  / 2;
		int marginY = (DUMP_OUT_H - nCpsScreenHeight) / 2;
		fprintf(m, "out_w %d\nout_h %d\nmargin_x %d\nmargin_y %d\n"
		           "screen_w %d\nscreen_h %d\ngx %d\ngy %d\nnative_w 384\nnative_h 224\n",
		        DUMP_OUT_W, DUMP_OUT_H, marginX, marginY,
		        nCpsScreenWidth, nCpsScreenHeight, nCpsGlobalXOffset, nCpsGlobalYOffset);
		fclose(m);
	}
	stageIdx++;
	return (r1 || r2 || r3) ? 1 : 0;
}

// Dump les 3 layers d'un coup (scroll1/2/3_dump.ppm).
extern "C" INT32 CpsDumpAllLayers()
{
	INT32 r1 = DumpLayer("scroll1_dump.ppm", 1);
	INT32 r2 = DumpLayer("scroll2_dump.ppm", 2);
	INT32 r3 = DumpLayer("scroll3_dump.ppm", 3);
	return (r1 || r2 || r3) ? 1 : 0;
}
